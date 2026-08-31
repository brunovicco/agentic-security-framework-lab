"""Deterministic vulnerability-analysis fixture."""

from typing import Final

from agentic_lab.application.evidence import (
    AssetInventoryItem,
    SecurityPolicy,
    VulnerabilityEvidence,
)

DEMO_CVE_ID: Final = "CVE-2026-9001"


_VULNERABILITY: Final[VulnerabilityEvidence] = {
    "cve_id": DEMO_CVE_ID,
    "product": "ExampleServer",
    "affected_before": "4.2",
    "severity": "critical",
    "cvss_score": "9.8",
    "epss_score": "0.91",
    "kev_listed": True,
}


_ASSETS: Final[tuple[AssetInventoryItem, ...]] = (
    {
        "asset_id": "api-prod-01",
        "product": "ExampleServer",
        "version": "4.1",
        "environment": "production",
        "network_exposure": "internet-exposed",
    },
    {
        "asset_id": "api-prod-02",
        "product": "ExampleServer",
        "version": "4.4",
        "environment": "production",
        "network_exposure": "internal",
    },
)


_POLICY: Final[SecurityPolicy] = {
    "policy_id": "POLICY-DEMO-001",
    "human_review_severity": "critical",
    "human_review_environment": "production",
    "human_review_network_exposure": "internet-exposed",
    "unknown_applicability_requires_review": True,
}


def load_vulnerability_evidence(cve_id: str) -> VulnerabilityEvidence:
    """Return deterministic vulnerability evidence for the demo CVE."""
    if cve_id != DEMO_CVE_ID:
        raise KeyError(f"Unknown demo CVE: {cve_id}")

    return _VULNERABILITY.copy()


def load_asset_inventory() -> tuple[AssetInventoryItem, ...]:
    """Return the deterministic demo asset inventory."""
    return tuple(item.copy() for item in _ASSETS)


def load_security_policy() -> SecurityPolicy:
    """Return the deterministic demo security policy."""
    return _POLICY.copy()
