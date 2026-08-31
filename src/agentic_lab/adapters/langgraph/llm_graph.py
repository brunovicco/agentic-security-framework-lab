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
    LLMAnalysisGraphOutput,
)
from agentic_lab.application.analyzer import VulnerabilityAnalyzer
from agentic_lab.application.contracts import (
    AnalysisResult,
    Severity,
)
from agentic_lab.application.oracle import (
    assess_assets_deterministically,
)


class _InvokableGraph(Protocol):
    """Minimal local boundary for a compiled LangGraph workflow."""

    def invoke(
        self,
        input: AnalysisGraphInput,
    ) -> LLMAnalysisGraphOutput:
        """Run the graph."""
        ...


def collect_evidence_node(
    state: AnalysisGraphState,
) -> AnalysisGraphState:
    """Adapt graph state to the deterministic evidence-collection node."""
    cve_id = state.get("cve_id")

    if cve_id is None:
        raise RuntimeError("Evidence collection requires a CVE identifier")

    graph_input: AnalysisGraphInput = {
        "cve_id": cve_id,
    }

    return collect_evidence(graph_input)


def analyze_with_llm(
    state: AnalysisGraphState,
    analyzer: VulnerabilityAnalyzer,
) -> AnalysisGraphState:
    """Produce a structured vulnerability analysis through an LLM."""
    vulnerability = state.get("vulnerability")
    assets = state.get("assets")

    if vulnerability is None or assets is None:
        raise RuntimeError("LLM analysis requires vulnerability and asset evidence")

    draft = analyzer.analyze(
        vulnerability=vulnerability,
        assets=assets,
    )

    return {
        "llm_draft": draft,
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
        }

    return {
        "validation_passed": False,
        "validation_reason": ("LLM applicability differs from deterministic oracle."),
    }


def route_after_validation(
    state: AnalysisGraphState,
) -> Literal["accepted", "rejected"]:
    """Route according to deterministic validation outcome."""
    validation_passed = state.get("validation_passed")

    if validation_passed is None:
        raise RuntimeError("Validation outcome is missing")

    return "accepted" if validation_passed else "rejected"


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
    """Replace invalid LLM applicability with deterministic results."""
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
            "LLM applicability was rejected; use deterministic "
            "assessment and review the disagreement."
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
    """Build the LLM-backed vulnerability-analysis workflow."""

    def llm_node(
        state: AnalysisGraphState,
    ) -> AnalysisGraphState:
        return analyze_with_llm(state, analyzer)

    builder = StateGraph(
        AnalysisGraphState,
        input_schema=AnalysisGraphInput,
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
    """Run the LLM-backed vulnerability-analysis graph."""
    graph = build_llm_analysis_graph(analyzer)

    graph_input: AnalysisGraphInput = {
        "cve_id": cve_id,
    }

    return graph.invoke(graph_input)
