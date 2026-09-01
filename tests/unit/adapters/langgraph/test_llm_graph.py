"""Tests for the evaluator-optimizer LangGraph workflow."""

import pytest

from agentic_lab.adapters.fixtures.demo import DEMO_CVE_ID
from agentic_lab.adapters.fixtures.evaluation import (
    load_evaluation_scenarios,
)
from agentic_lab.adapters.langgraph.llm_graph import (
    build_llm_analysis_graph,
    run_llm_analysis_graph,
    run_llm_analysis_graph_with_evidence,
)
from agentic_lab.adapters.langgraph.state import LLMAnalysisGraphInput
from agentic_lab.application.contracts import (
    AssetAssessment,
    LLMAnalysisDraft,
)
from agentic_lab.application.evidence import (
    AnalysisEvidenceBundle,
    AssetInventoryItem,
    VulnerabilityEvidence,
)


class SequentialStubAnalyzer:
    """Return predetermined drafts in sequence and record evaluator feedback."""

    def __init__(
        self,
        drafts: tuple[LLMAnalysisDraft, ...],
    ) -> None:
        self._drafts = drafts
        self._index = 0
        self.feedbacks: list[str | None] = []

    def analyze(
        self,
        vulnerability: VulnerabilityEvidence,
        assets: tuple[AssetInventoryItem, ...],
        feedback: str | None = None,
    ) -> LLMAnalysisDraft:
        """Return the next configured structured draft."""
        del vulnerability, assets

        self.feedbacks.append(feedback)

        draft = self._drafts[self._index]
        self._index += 1

        return draft


def correct_draft(
    recommendation: str = "Patch api-prod-01.",
    confidence: float = 0.92,
) -> LLMAnalysisDraft:
    """Return the deterministic-oracle-compatible LLM draft."""
    return LLMAnalysisDraft(
        assets=(
            AssetAssessment(
                asset_id="api-prod-01",
                status="affected",
                rationale="ExampleServer 4.1 is below 4.2.",
            ),
            AssetAssessment(
                asset_id="api-prod-02",
                status="not_affected",
                rationale="ExampleServer 4.4 is not below 4.2.",
            ),
        ),
        recommendation=recommendation,
        confidence=confidence,
    )


def incorrect_draft() -> LLMAnalysisDraft:
    """Return an intentionally unsafe applicability conclusion."""
    return LLMAnalysisDraft(
        assets=(
            AssetAssessment(
                asset_id="api-prod-01",
                status="not_affected",
                rationale="Incorrect LLM conclusion.",
            ),
            AssetAssessment(
                asset_id="api-prod-02",
                status="not_affected",
                rationale="Version appears safe.",
            ),
        ),
        recommendation="No remediation required.",
        confidence=0.99,
    )


def test_llm_graph_accepts_correct_first_attempt() -> None:
    """Accept an LLM analysis that matches the oracle immediately."""
    analyzer = SequentialStubAnalyzer(
        drafts=(correct_draft(),),
    )

    output = run_llm_analysis_graph(
        analyzer,
        DEMO_CVE_ID,
    )

    assert output["analysis_source"] == "llm"
    assert output["validation_passed"]
    assert output["analysis_attempts"] == 1
    assert analyzer.feedbacks == [None]

    attempt_trace = output["attempt_trace"]
    assert len(attempt_trace) == 1
    assert attempt_trace[0].attempt == 1
    assert attempt_trace[0].input_feedback is None
    assert attempt_trace[0].validation_passed is True
    assert attempt_trace[0].draft == correct_draft()

    assert output["result"].recommendation == "Patch api-prod-01."
    assert output["result"].confidence == 0.92


def test_llm_graph_recovers_after_evaluator_feedback() -> None:
    """Retry a rejected draft and accept the corrected second attempt."""
    analyzer = SequentialStubAnalyzer(
        drafts=(
            incorrect_draft(),
            correct_draft(
                recommendation="Patch after evaluator correction.",
                confidence=0.97,
            ),
        ),
    )

    output = run_llm_analysis_graph(
        analyzer,
        DEMO_CVE_ID,
    )

    assert output["analysis_source"] == "llm"
    assert output["validation_passed"]
    assert output["analysis_attempts"] == 2

    assert analyzer.feedbacks[0] is None
    assert analyzer.feedbacks[1] is not None
    assert "api-prod-01" in analyzer.feedbacks[1]

    attempt_trace = output["attempt_trace"]
    assert len(attempt_trace) == 2
    first_attempt, second_attempt = attempt_trace
    assert first_attempt.attempt == 1
    assert first_attempt.validation_passed is False
    assert first_attempt.input_feedback is None
    assert second_attempt.attempt == 2
    assert second_attempt.validation_passed is True
    assert second_attempt.input_feedback == first_attempt.validation_feedback

    assert output["result"].recommendation == "Patch after evaluator correction."
    assert output["result"].confidence == 0.97


def test_llm_graph_falls_back_after_retry_is_exhausted() -> None:
    """Fall back when both LLM attempts disagree with the oracle."""
    analyzer = SequentialStubAnalyzer(
        drafts=(
            incorrect_draft(),
            incorrect_draft(),
        ),
    )

    output = run_llm_analysis_graph(
        analyzer,
        DEMO_CVE_ID,
    )
    result = output["result"]

    statuses = {assessment.asset_id: assessment.status for assessment in result.assets}

    assert output["analysis_source"] == "oracle_fallback"
    assert not output["validation_passed"]
    assert output["analysis_attempts"] == 2

    assert len(analyzer.feedbacks) == 2
    assert analyzer.feedbacks[0] is None
    assert analyzer.feedbacks[1] is not None

    attempt_trace = output["attempt_trace"]
    assert len(attempt_trace) == 2
    first_attempt, second_attempt = attempt_trace
    assert first_attempt.validation_passed is False
    assert second_attempt.validation_passed is False
    assert second_attempt.input_feedback == first_attempt.validation_feedback

    assert statuses == {
        "api-prod-01": "affected",
        "api-prod-02": "not_affected",
    }

    assert result.recommendation.startswith("LLM applicability remained invalid after retry")
    assert result.confidence == 1.0
    assert result.requires_human_review


def test_llm_graph_accepts_injected_evaluation_evidence() -> None:
    """Run the same graph with a framework-neutral evaluation scenario."""
    scenario = next(
        scenario
        for scenario in load_evaluation_scenarios()
        if scenario.scenario_id == "product-mismatch"
    )

    evidence_bundle: AnalysisEvidenceBundle = {
        "vulnerability": scenario.vulnerability,
        "assets": scenario.assets,
        "policy": scenario.policy,
    }

    analyzer = SequentialStubAnalyzer(
        drafts=(
            LLMAnalysisDraft(
                assets=(
                    AssetAssessment(
                        asset_id="api-prod-03",
                        status="not_applicable",
                        rationale=(
                            "OtherServer does not match the vulnerable ExampleServer product."
                        ),
                    ),
                ),
                recommendation=("No remediation is required for this asset."),
                confidence=0.99,
            ),
        ),
    )

    output = run_llm_analysis_graph_with_evidence(
        analyzer=analyzer,
        evidence_bundle=evidence_bundle,
    )

    assert output["analysis_source"] == "llm"
    assert output["validation_passed"]
    assert output["analysis_attempts"] == 1
    assert len(output["attempt_trace"]) == 1
    assert output["attempt_trace"][0].validation_passed is True

    result = output["result"]

    assert result.cve_id == "CVE-2026-9102"
    assert len(result.assets) == 1
    assert result.assets[0].asset_id == "api-prod-03"
    assert result.assets[0].status == "not_applicable"


def test_llm_graph_rejects_mismatched_injected_cve_id() -> None:
    """Reject injected evidence when its CVE identity is inconsistent."""
    scenario = next(
        scenario
        for scenario in load_evaluation_scenarios()
        if scenario.scenario_id == "product-mismatch"
    )

    evidence_bundle: AnalysisEvidenceBundle = {
        "vulnerability": scenario.vulnerability,
        "assets": scenario.assets,
        "policy": scenario.policy,
    }

    analyzer = SequentialStubAnalyzer(
        drafts=(
            LLMAnalysisDraft(
                assets=(),
                recommendation="Unused.",
                confidence=0.0,
            ),
        ),
    )

    graph = build_llm_analysis_graph(analyzer)

    mismatched_input: LLMAnalysisGraphInput = {
        "cve_id": "CVE-2026-9999",
        "evidence_bundle": evidence_bundle,
    }

    with pytest.raises(
        RuntimeError,
        match="Injected evidence CVE identifier does not match graph input",
    ):
        graph.invoke(mismatched_input)
