"""LangChain tools backed by deterministic demo evidence."""

from langchain.tools import tool

from agentic_lab.adapters.fixtures.demo import (
    load_asset_inventory,
    load_security_policy,
    load_vulnerability_evidence,
)
from agentic_lab.application.evidence import (
    AssetInventoryItem,
    SecurityPolicy,
    VulnerabilityEvidence,
)


@tool
def get_vulnerability_evidence(cve_id: str) -> VulnerabilityEvidence:
    """Get deterministic vulnerability evidence for one CVE."""
    return load_vulnerability_evidence(cve_id)


@tool
def get_asset_inventory() -> tuple[AssetInventoryItem, ...]:
    """Get the assets and installed software visible to the analysis."""
    return load_asset_inventory()


@tool
def get_security_policy() -> SecurityPolicy:
    """Get the deterministic human-review security policy."""
    return load_security_policy()


ANALYSIS_TOOLS = (
    get_vulnerability_evidence,
    get_asset_inventory,
    get_security_policy,
)
