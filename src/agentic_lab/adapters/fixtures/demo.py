"""Deterministic vulnerability-analysis fixture."""

from typing import Final, TypedDict


class VulnerabilityEvidence(TypedDict):
    """Structured vulnerability evidence returned by the demo source."""

    cve_id: str
    product: str
    affected_before: str
    severity: str
    cvss_score: str
    epss_score: str
    kev_listed: bool


class AssetInventoryItem(TypedDict):
    """Structured asset inventory entry used by the demo workload."""

    asset_id: str
    product: str
    version: str
    environment: str
    network_exposure: str


class SecurityPolicy(TypedDict):
    """Structured deterministic policy used by the demo workload."""

    policy_id: str
    human_review_severity: str
    human_review_environment: str
    human_review_network_exposure: str
    unknown_applicability_requires_review: bool


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
