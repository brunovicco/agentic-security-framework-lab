"""Tests for the LLM-backed LangGraph vulnerability-analysis workflow."""

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


class StubAnalyzer:
    """Return predetermined structured analysis drafts."""

    def __init__(
        self,
        draft: LLMAnalysisDraft,
    ) -> None:
        self._draft = draft

    def analyze(
        self,
        vulnerability: VulnerabilityEvidence,
        assets: tuple[AssetInventoryItem, ...],
    ) -> LLMAnalysisDraft:
        """Return the configured structured draft."""
        del vulnerability, assets
        return self._draft


def test_llm_graph_accepts_analysis_matching_oracle() -> None:
    """Accept LLM applicability when it matches deterministic truth."""
    analyzer = StubAnalyzer(
        LLMAnalysisDraft(
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
            recommendation="Patch api-prod-01.",
            confidence=0.92,
        )
    )

    output = run_llm_analysis_graph(
        analyzer,
        DEMO_CVE_ID,
    )
    result = output["result"]

    assert output["analysis_source"] == "llm"
    assert output["validation_passed"]
    assert output["validation_reason"] == ("LLM applicability matches deterministic oracle.")

    assert result.recommendation == "Patch api-prod-01."
    assert result.confidence == 0.92
    assert result.requires_human_review


def test_llm_graph_falls_back_when_llm_disagrees_with_oracle() -> None:
    """Reject unsafe LLM applicability and fall back deterministically."""
    analyzer = StubAnalyzer(
        LLMAnalysisDraft(
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
    )

    output = run_llm_analysis_graph(
        analyzer,
        DEMO_CVE_ID,
    )
    result = output["result"]

    statuses = {assessment.asset_id: assessment.status for assessment in result.assets}

    assert output["analysis_source"] == "oracle_fallback"
    assert not output["validation_passed"]
    assert output["validation_reason"] == ("LLM applicability differs from deterministic oracle.")

    assert statuses == {
        "api-prod-01": "affected",
        "api-prod-02": "not_affected",
    }

    assert result.recommendation.startswith("LLM applicability was rejected")
    assert result.confidence == 1.0
    assert result.requires_human_review
