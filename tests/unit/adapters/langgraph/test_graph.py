"""Tests for the deterministic LangGraph vulnerability-analysis workflow."""

from agentic_lab.adapters.fixtures.demo import DEMO_CVE_ID
from agentic_lab.adapters.langgraph.graph import run_analysis_graph


def test_langgraph_analyzes_demo_vulnerability_end_to_end() -> None:
    """Run the deterministic demo workload through LangGraph."""
    output = run_analysis_graph(DEMO_CVE_ID)

    result = output["result"]

    assert result.cve_id == DEMO_CVE_ID
    assert result.severity == "critical"
    assert result.requires_human_review

    statuses = {assessment.asset_id: assessment.status for assessment in result.assets}

    assert statuses == {
        "api-prod-01": "affected",
        "api-prod-02": "not_affected",
    }


def test_langgraph_preserves_evidence_references() -> None:
    """Return explicit evidence references from the graph."""
    output = run_analysis_graph(DEMO_CVE_ID)

    assert output["result"].evidence == (
        "fixture:vulnerability",
        "fixture:asset-inventory",
        "fixture:security-policy",
    )
