"""Framework-neutral deterministic validation and fallback workflow."""

from collections import Counter
from dataclasses import dataclass
from typing import Literal, cast

from agentic_lab.application.analyzer import VulnerabilityAnalyzer
from agentic_lab.application.contracts import (
    AnalysisResult,
    AssetAssessment,
    LLMAnalysisDraft,
    Severity,
)
from agentic_lab.application.evidence import (
    AnalysisEvidenceBundle,
    AssetInventoryItem,
    SecurityPolicy,
    VulnerabilityEvidence,
)
from agentic_lab.application.oracle import assess_assets_deterministically

DEFAULT_MAX_ANALYSIS_ATTEMPTS = 2
AnalysisSource = Literal["llm", "oracle_fallback"]


@dataclass(frozen=True, slots=True)
class DraftValidation:
    """Represent deterministic validation of one LLM analysis draft."""

    passed: bool
    reason: str
    feedback: str


@dataclass(frozen=True, slots=True)
class ValidatedAnalysisOutput:
    """Represent one validated framework-neutral analysis execution."""

    result: AnalysisResult
    analysis_source: AnalysisSource
    validation_passed: bool
    validation_reason: str
    analysis_attempts: int


def validate_analysis_draft(
    vulnerability: VulnerabilityEvidence,
    assets: tuple[AssetInventoryItem, ...],
    draft: LLMAnalysisDraft,
) -> DraftValidation:
    """Compare LLM applicability decisions with deterministic ground truth."""
    oracle = assess_assets_deterministically(
        vulnerability=vulnerability,
        assets=assets,
    )

    expected = {assessment.asset_id: assessment.status for assessment in oracle}
    observed = {assessment.asset_id: assessment.status for assessment in draft.assets}
    expected_counts = Counter(assessment.asset_id for assessment in oracle)
    observed_counts = Counter(assessment.asset_id for assessment in draft.assets)

    if observed == expected and observed_counts == expected_counts:
        return DraftValidation(
            passed=True,
            reason="LLM applicability matches deterministic oracle.",
            feedback="",
        )

    asset_ids = sorted(set(expected) | set(observed) | set(expected_counts) | set(observed_counts))
    mismatched_assets = [
        asset_id
        for asset_id in asset_ids
        if expected.get(asset_id) != observed.get(asset_id)
        or expected_counts.get(asset_id, 0) != observed_counts.get(asset_id, 0)
    ]

    mismatch_text = ", ".join(mismatched_assets) or "unknown asset set"

    return DraftValidation(
        passed=False,
        reason="LLM applicability differs from deterministic oracle.",
        feedback=(
            f"Applicability mismatch for assets: {mismatch_text}. "
            "Re-check product identity and compare installed versions "
            "against the affected_before boundary using numeric "
            "major.minor ordering. Return each supplied asset exactly once "
            "and use only the supplied evidence."
        ),
    )


def evaluate_human_review_policy(
    vulnerability: VulnerabilityEvidence,
    assets: tuple[AssetInventoryItem, ...],
    policy: SecurityPolicy,
    assessments: tuple[AssetAssessment, ...],
) -> bool:
    """Apply deterministic human-review policy to validated assessments."""
    assets_by_id = {asset["asset_id"]: asset for asset in assets}

    for assessment in assessments:
        if assessment.status == "unknown" and policy["unknown_applicability_requires_review"]:
            return True

        if assessment.status != "affected":
            continue

        asset = assets_by_id.get(assessment.asset_id)

        if asset is None:
            raise RuntimeError("Policy evaluation received an assessment for an unknown asset")

        if (
            vulnerability["severity"] == policy["human_review_severity"]
            and asset["environment"] == policy["human_review_environment"]
            and asset["network_exposure"] == policy["human_review_network_exposure"]
        ):
            return True

    return False


def _build_result(
    vulnerability: VulnerabilityEvidence,
    assessments: tuple[AssetAssessment, ...],
    recommendation: str,
    confidence: float,
    requires_human_review: bool,
) -> AnalysisResult:
    """Build the shared framework-independent result contract."""
    return AnalysisResult(
        cve_id=vulnerability["cve_id"],
        severity=cast(Severity, vulnerability["severity"]),
        assets=assessments,
        recommendation=recommendation,
        confidence=confidence,
        evidence=(
            "fixture:vulnerability",
            "fixture:asset-inventory",
            "fixture:security-policy",
        ),
        requires_human_review=requires_human_review,
    )


def run_validated_analysis(
    analyzer: VulnerabilityAnalyzer,
    evidence_bundle: AnalysisEvidenceBundle,
    max_attempts: int = DEFAULT_MAX_ANALYSIS_ATTEMPTS,
) -> ValidatedAnalysisOutput:
    """Run bounded LLM analysis with deterministic validation and fallback."""
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")

    vulnerability = evidence_bundle["vulnerability"]
    assets = evidence_bundle["assets"]
    policy = evidence_bundle["policy"]
    feedback: str | None = None

    for attempt in range(1, max_attempts + 1):
        draft = analyzer.analyze(
            vulnerability=vulnerability,
            assets=assets,
            feedback=feedback,
        )
        validation = validate_analysis_draft(
            vulnerability=vulnerability,
            assets=assets,
            draft=draft,
        )

        if validation.passed:
            requires_human_review = evaluate_human_review_policy(
                vulnerability=vulnerability,
                assets=assets,
                policy=policy,
                assessments=draft.assets,
            )
            return ValidatedAnalysisOutput(
                result=_build_result(
                    vulnerability=vulnerability,
                    assessments=draft.assets,
                    recommendation=draft.recommendation,
                    confidence=draft.confidence,
                    requires_human_review=requires_human_review,
                ),
                analysis_source="llm",
                validation_passed=True,
                validation_reason=validation.reason,
                analysis_attempts=attempt,
            )

        feedback = validation.feedback

    assessments = assess_assets_deterministically(
        vulnerability=vulnerability,
        assets=assets,
    )
    requires_human_review = evaluate_human_review_policy(
        vulnerability=vulnerability,
        assets=assets,
        policy=policy,
        assessments=assessments,
    )

    return ValidatedAnalysisOutput(
        result=_build_result(
            vulnerability=vulnerability,
            assessments=assessments,
            recommendation=(
                "LLM applicability remained invalid after retry; use "
                "deterministic assessment and review the disagreement."
            ),
            confidence=1.0,
            requires_human_review=requires_human_review,
        ),
        analysis_source="oracle_fallback",
        validation_passed=False,
        validation_reason=validation.reason,
        analysis_attempts=max_attempts,
    )
