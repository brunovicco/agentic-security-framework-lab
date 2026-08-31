"""LangGraph workflow combining LLM reasoning with deterministic validation."""

# LangGraph's public typing surface contains partial/unknown types under Pyright
# strict mode. Keep those diagnostics isolated at this framework boundary.
# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false

from typing import Literal, Protocol, cast

from langgraph.graph import END, START, StateGraph

from agentic_lab.adapters.langgraph.graph import (
    apply_policy,
    collect_evidence,
)
from agentic_lab.adapters.langgraph.state import (
    AnalysisGraphInput,
    AnalysisGraphState,
    LLMAnalysisGraphInput,
    LLMAnalysisGraphOutput,
)
from agentic_lab.application.analyzer import VulnerabilityAnalyzer
from agentic_lab.application.contracts import (
    AnalysisResult,
    Severity,
)
from agentic_lab.application.evidence import AnalysisEvidenceBundle
from agentic_lab.application.oracle import (
    assess_assets_deterministically,
)

_MAX_ANALYSIS_ATTEMPTS = 2


class _InvokableGraph(Protocol):
    """Minimal local boundary for a compiled LangGraph workflow."""

    def invoke(
        self,
        input: LLMAnalysisGraphInput,
    ) -> LLMAnalysisGraphOutput:
        """Run the graph."""
        ...


def collect_evidence_node(
    state: AnalysisGraphState,
) -> AnalysisGraphState:
    """Adapt graph state to deterministic evidence collection."""
    cve_id = state.get("cve_id")

    if cve_id is None:
        raise RuntimeError("Evidence collection requires a CVE identifier")

    evidence_bundle = state.get("evidence_bundle")

    if evidence_bundle is not None:
        evidence_cve_id = evidence_bundle["vulnerability"]["cve_id"]

        if evidence_cve_id != cve_id:
            raise RuntimeError("Injected evidence CVE identifier does not match graph input")

        return {
            "vulnerability": evidence_bundle["vulnerability"],
            "assets": evidence_bundle["assets"],
            "policy": evidence_bundle["policy"],
        }

    graph_input: AnalysisGraphInput = {
        "cve_id": cve_id,
    }

    return collect_evidence(graph_input)


def analyze_with_llm(
    state: AnalysisGraphState,
    analyzer: VulnerabilityAnalyzer,
) -> AnalysisGraphState:
    """Produce or refine structured vulnerability analysis through an LLM."""
    vulnerability = state.get("vulnerability")
    assets = state.get("assets")

    if vulnerability is None or assets is None:
        raise RuntimeError("LLM analysis requires vulnerability and asset evidence")

    previous_attempts = state.get("analysis_attempts", 0)
    feedback = state.get("validation_feedback")

    draft = analyzer.analyze(
        vulnerability=vulnerability,
        assets=assets,
        feedback=feedback if previous_attempts > 0 else None,
    )

    return {
        "llm_draft": draft,
        "analysis_attempts": previous_attempts + 1,
    }


def validate_against_oracle(
    state: AnalysisGraphState,
) -> AnalysisGraphState:
    """Compare LLM applicability decisions with deterministic ground truth."""
    vulnerability = state.get("vulnerability")
    assets = state.get("assets")
    draft = state.get("llm_draft")

    if vulnerability is None or assets is None or draft is None:
        raise RuntimeError("LLM validation requires evidence and a structured draft")

    oracle = assess_assets_deterministically(
        vulnerability=vulnerability,
        assets=assets,
    )

    expected = {assessment.asset_id: assessment.status for assessment in oracle}
    observed = {assessment.asset_id: assessment.status for assessment in draft.assets}

    if observed == expected:
        return {
            "validation_passed": True,
            "validation_reason": ("LLM applicability matches deterministic oracle."),
            "validation_feedback": "",
        }

    asset_ids = sorted(set(expected) | set(observed))
    mismatched_assets = [
        asset_id for asset_id in asset_ids if expected.get(asset_id) != observed.get(asset_id)
    ]

    mismatch_text = ", ".join(mismatched_assets)

    return {
        "validation_passed": False,
        "validation_reason": ("LLM applicability differs from deterministic oracle."),
        "validation_feedback": (
            f"Applicability mismatch for assets: {mismatch_text}. "
            "Re-check product identity and compare installed versions "
            "against the affected_before boundary using numeric "
            "major.minor ordering. Use only the supplied evidence."
        ),
    }


def route_after_validation(
    state: AnalysisGraphState,
) -> Literal["accepted", "retry", "rejected"]:
    """Accept, retry, or fall back according to deterministic validation."""
    validation_passed = state.get("validation_passed")

    if validation_passed is None:
        raise RuntimeError("Validation outcome is missing")

    if validation_passed:
        return "accepted"

    attempts = state.get("analysis_attempts", 0)

    if attempts < _MAX_ANALYSIS_ATTEMPTS:
        return "retry"

    return "rejected"


def use_llm_analysis(
    state: AnalysisGraphState,
) -> AnalysisGraphState:
    """Accept validated LLM reasoning for downstream processing."""
    draft = state.get("llm_draft")

    if draft is None:
        raise RuntimeError("Validated LLM draft is missing")

    return {
        "assessments": draft.assets,
        "recommendation": draft.recommendation,
        "confidence": draft.confidence,
        "analysis_source": "llm",
    }


def fallback_to_oracle(
    state: AnalysisGraphState,
) -> AnalysisGraphState:
    """Replace repeatedly invalid LLM applicability with deterministic results."""
    vulnerability = state.get("vulnerability")
    assets = state.get("assets")

    if vulnerability is None or assets is None:
        raise RuntimeError("Oracle fallback requires vulnerability and asset evidence")

    assessments = assess_assets_deterministically(
        vulnerability=vulnerability,
        assets=assets,
    )

    return {
        "assessments": assessments,
        "recommendation": (
            "LLM applicability remained invalid after retry; use "
            "deterministic assessment and review the disagreement."
        ),
        "confidence": 1.0,
        "analysis_source": "oracle_fallback",
    }


def finalize_llm_analysis(
    state: AnalysisGraphState,
) -> AnalysisGraphState:
    """Build the shared result after validated or fallback analysis."""
    cve_id = state.get("cve_id")
    vulnerability = state.get("vulnerability")
    assessments = state.get("assessments")
    recommendation = state.get("recommendation")
    confidence = state.get("confidence")
    requires_human_review = state.get("requires_human_review")

    if (
        cve_id is None
        or vulnerability is None
        or assessments is None
        or recommendation is None
        or confidence is None
        or requires_human_review is None
    ):
        raise RuntimeError("Finalization requires complete validated analysis state")

    result = AnalysisResult(
        cve_id=cve_id,
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

    return {
        "result": result,
    }


def build_llm_analysis_graph(
    analyzer: VulnerabilityAnalyzer,
) -> _InvokableGraph:
    """Build the evaluator-optimizer vulnerability-analysis workflow."""

    def llm_node(
        state: AnalysisGraphState,
    ) -> AnalysisGraphState:
        return analyze_with_llm(state, analyzer)

    builder = StateGraph(
        AnalysisGraphState,
        input_schema=LLMAnalysisGraphInput,
        output_schema=LLMAnalysisGraphOutput,
    )

    builder.add_node("collect_evidence", collect_evidence_node)
    builder.add_node("analyze_with_llm", llm_node)
    builder.add_node(
        "validate_against_oracle",
        validate_against_oracle,
    )
    builder.add_node("use_llm_analysis", use_llm_analysis)
    builder.add_node("fallback_to_oracle", fallback_to_oracle)
    builder.add_node("apply_policy", apply_policy)
    builder.add_node("finalize", finalize_llm_analysis)

    builder.add_edge(START, "collect_evidence")
    builder.add_edge(
        "collect_evidence",
        "analyze_with_llm",
    )
    builder.add_edge(
        "analyze_with_llm",
        "validate_against_oracle",
    )

    builder.add_conditional_edges(
        "validate_against_oracle",
        route_after_validation,
        {
            "accepted": "use_llm_analysis",
            "retry": "analyze_with_llm",
            "rejected": "fallback_to_oracle",
        },
    )

    builder.add_edge(
        "use_llm_analysis",
        "apply_policy",
    )
    builder.add_edge(
        "fallback_to_oracle",
        "apply_policy",
    )
    builder.add_edge("apply_policy", "finalize")
    builder.add_edge("finalize", END)

    return cast(_InvokableGraph, builder.compile())


def run_llm_analysis_graph(
    analyzer: VulnerabilityAnalyzer,
    cve_id: str,
) -> LLMAnalysisGraphOutput:
    """Run the evaluator-optimizer vulnerability-analysis graph."""
    graph = build_llm_analysis_graph(analyzer)

    graph_input: LLMAnalysisGraphInput = {
        "cve_id": cve_id,
    }

    return graph.invoke(graph_input)


def run_llm_analysis_graph_with_evidence(
    analyzer: VulnerabilityAnalyzer,
    evidence_bundle: AnalysisEvidenceBundle,
) -> LLMAnalysisGraphOutput:
    """Run the graph using evidence supplied by the application."""
    graph = build_llm_analysis_graph(analyzer)

    graph_input: LLMAnalysisGraphInput = {
        "cve_id": evidence_bundle["vulnerability"]["cve_id"],
        "evidence_bundle": evidence_bundle,
    }

    return graph.invoke(graph_input)
