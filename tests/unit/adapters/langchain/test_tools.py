"""Tests for LangChain vulnerability-analysis tools."""

from typing import cast

from agentic_lab.adapters.fixtures.demo import DEMO_CVE_ID
from agentic_lab.adapters.langchain.tools import (
    get_asset_inventory,
    get_security_policy,
    get_vulnerability_evidence,
)
from agentic_lab.application.evidence import (
    AssetInventoryItem,
    SecurityPolicy,
    VulnerabilityEvidence,
)


def test_langchain_vulnerability_tool_exposes_demo_evidence() -> None:
    """Expose deterministic vulnerability evidence through LangChain."""
    result = cast(
        VulnerabilityEvidence,
        get_vulnerability_evidence.invoke({"cve_id": DEMO_CVE_ID}),
    )

    assert result["product"] == "ExampleServer"


def test_langchain_inventory_tool_exposes_demo_assets() -> None:
    """Expose deterministic inventory evidence through LangChain."""
    result = cast(
        tuple[AssetInventoryItem, ...],
        get_asset_inventory.invoke({}),
    )

    assert len(result) == 2


def test_langchain_policy_tool_exposes_demo_policy() -> None:
    """Expose deterministic policy through LangChain."""
    result = cast(
        SecurityPolicy,
        get_security_policy.invoke({}),
    )

    assert result["policy_id"] == "POLICY-DEMO-001"
