"""Tests for framework-neutral deterministic validation and fallback."""

from agentic_lab.adapters.fixtures.evaluation import load_evaluation_scenarios
from agentic_lab.application.contracts import (
    ApplicabilityStatus,
    AssetAssessment,
    LLMAnalysisDraft,
)
from agentic_lab.application.evidence import (
    AnalysisEvidenceBundle,
    AssetInventoryItem,
    VulnerabilityEvidence,
)
from agentic_lab.application.validated_analysis import (
    run_validated_analysis,
    validate_analysis_draft,
)


class SequencedAnalyzer:
    """Return predefined drafts while capturing evaluator feedback."""

    def __init__(self, drafts: tuple[LLMAnalysisDraft, ...]) -> None:
        self._drafts = drafts
        self.feedback: list[str | None] = []

    def analyze(
        self,
        vulnerability: VulnerabilityEvidence,
        assets: tuple[AssetInventoryItem, ...],
        feedback: str | None = None,
    ) -> LLMAnalysisDraft:
        del vulnerability, assets
        self.feedback.append(feedback)
        index = min(len(self.feedback) - 1, len(self._drafts) - 1)
        return self._drafts[index]


def _bundle(scenario_id: str) -> AnalysisEvidenceBundle:
    scenario = next(
        scenario for scenario in load_evaluation_scenarios() if scenario.scenario_id == scenario_id
    )
    return {
        "vulnerability": scenario.vulnerability,
        "assets": scenario.assets,
        "policy": scenario.policy,
    }


def _draft(
    asset_id: str,
    status: ApplicabilityStatus,
    confidence: float = 0.9,
) -> LLMAnalysisDraft:
    return LLMAnalysisDraft(
        assets=(
            AssetAssessment(
                asset_id=asset_id,
                status=status,
                rationale="Stub applicability rationale.",
            ),
        ),
        recommendation="Apply the validated remediation path.",
        confidence=confidence,
    )


def test_validated_analysis_accepts_correct_first_attempt() -> None:
    analyzer = SequencedAnalyzer((_draft("api-prod-03", "not_applicable"),))

    output = run_validated_analysis(
        analyzer=analyzer,
        evidence_bundle=_bundle("product-mismatch"),
    )

    assert output.analysis_source == "llm"
    assert output.validation_passed is True
    assert output.analysis_attempts == 1
    assert output.result.assets[0].status == "not_applicable"
    assert analyzer.feedback == [None]


def test_validated_analysis_retries_with_deterministic_feedback() -> None:
    analyzer = SequencedAnalyzer(
        (
            _draft("api-prod-03", "affected"),
            _draft("api-prod-03", "not_applicable"),
        )
    )

    output = run_validated_analysis(
        analyzer=analyzer,
        evidence_bundle=_bundle("product-mismatch"),
    )

    assert output.analysis_source == "llm"
    assert output.validation_passed is True
    assert output.analysis_attempts == 2
    assert analyzer.feedback[0] is None
    assert analyzer.feedback[1] is not None
    assert "api-prod-03" in analyzer.feedback[1]


def test_validated_analysis_falls_back_after_bounded_retries() -> None:
    analyzer = SequencedAnalyzer(
        (
            _draft("api-prod-03", "affected"),
            _draft("api-prod-03", "affected"),
        )
    )

    output = run_validated_analysis(
        analyzer=analyzer,
        evidence_bundle=_bundle("product-mismatch"),
    )

    assert output.analysis_source == "oracle_fallback"
    assert output.validation_passed is False
    assert output.analysis_attempts == 2
    assert output.result.assets[0].status == "not_applicable"
    assert output.result.confidence == 1.0


def test_validated_analysis_applies_unknown_review_policy() -> None:
    analyzer = SequencedAnalyzer((_draft("api-prod-04", "unknown"),))

    output = run_validated_analysis(
        analyzer=analyzer,
        evidence_bundle=_bundle("unknown-version"),
    )

    assert output.analysis_source == "llm"
    assert output.result.requires_human_review is True


def test_validation_rejects_duplicate_assets_even_when_status_matches() -> None:
    bundle = _bundle("product-mismatch")
    duplicated = LLMAnalysisDraft(
        assets=(
            AssetAssessment(
                asset_id="api-prod-03",
                status="not_applicable",
                rationale="First duplicate.",
            ),
            AssetAssessment(
                asset_id="api-prod-03",
                status="not_applicable",
                rationale="Second duplicate.",
            ),
        ),
        recommendation="No remediation required for this product mismatch.",
        confidence=0.9,
    )

    validation = validate_analysis_draft(
        vulnerability=bundle["vulnerability"],
        assets=bundle["assets"],
        draft=duplicated,
    )

    assert validation.passed is False
    assert "Return each supplied asset exactly once" in validation.feedback


def test_validated_analysis_rejects_invalid_attempt_limit() -> None:
    analyzer = SequencedAnalyzer((_draft("api-prod-03", "not_applicable"),))

    try:
        run_validated_analysis(
            analyzer=analyzer,
            evidence_bundle=_bundle("product-mismatch"),
            max_attempts=0,
        )
    except ValueError as exc:
        assert str(exc) == "max_attempts must be at least 1"
    else:
        raise AssertionError("Expected invalid attempt limit to be rejected")
