"""Tests for the LangChain structured vulnerability analyzer."""

from langchain_core.runnables import RunnableLambda

from agentic_lab.adapters.fixtures.demo import (
    DEMO_CVE_ID,
    load_asset_inventory,
    load_vulnerability_evidence,
)
from agentic_lab.adapters.langchain.analyzer import (
    LangChainVulnerabilityAnalyzer,
)
from agentic_lab.application.contracts import (
    AssetAssessment,
    LLMAnalysisDraft,
)


def test_analyzer_returns_structured_llm_draft() -> None:
    """Return structured analysis without requiring a real model provider."""
    draft = LLMAnalysisDraft(
        assets=(
            AssetAssessment(
                asset_id="api-prod-01",
                status="affected",
                rationale="Version 4.1 is below 4.2.",
            ),
            AssetAssessment(
                asset_id="api-prod-02",
                status="not_affected",
                rationale="Version 4.4 is not below 4.2.",
            ),
        ),
        recommendation="Prioritize remediation for api-prod-01.",
        confidence=0.95,
    )

    captured_inputs: list[object] = []

    def return_draft(model_input: object) -> LLMAnalysisDraft:
        captured_inputs.append(model_input)
        return draft

    analyzer = object.__new__(LangChainVulnerabilityAnalyzer)
    object.__setattr__(
        analyzer,
        "_model",
        RunnableLambda(return_draft),
    )

    result = analyzer.analyze(
        vulnerability=load_vulnerability_evidence(DEMO_CVE_ID),
        assets=load_asset_inventory(),
    )

    assert result == draft
    assert captured_inputs
    assert "ExampleServer" in str(captured_inputs[0])
    assert "api-prod-01" in str(captured_inputs[0])
