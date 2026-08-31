"""Tests for the evaluator-optimizer LangGraph workflow."""

from agentic_lab.adapters.fixtures.demo import DEMO_CVE_ID
from agentic_lab.adapters.langgraph.llm_graph import (
    run_llm_analysis_graph,
)
from agentic_lab.application.contracts import (
    AssetAssessment,
    LLMAnalysisDraft,
)
from agentic_lab.application.evidence import (
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

    assert statuses == {
        "api-prod-01": "affected",
        "api-prod-02": "not_affected",
    }

    assert result.recommendation.startswith("LLM applicability remained invalid after retry")
    assert result.confidence == 1.0
    assert result.requires_human_review
