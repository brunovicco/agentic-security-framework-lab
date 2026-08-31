"""Shared evidence contracts for vulnerability analysis."""

from typing import TypedDict


class VulnerabilityEvidence(TypedDict):
    """Structured vulnerability evidence."""

    cve_id: str
    product: str
    affected_before: str
    severity: str
    cvss_score: str
    epss_score: str
    kev_listed: bool


class AssetInventoryItem(TypedDict):
    """Structured asset inventory evidence."""

    asset_id: str
    product: str
    version: str
    environment: str
    network_exposure: str


class SecurityPolicy(TypedDict):
    """Structured deterministic security policy."""

    policy_id: str
    human_review_severity: str
    human_review_environment: str
    human_review_network_exposure: str
    unknown_applicability_requires_review: bool


class AnalysisEvidenceBundle(TypedDict):
    """Group evidence required for one vulnerability-analysis execution."""

    vulnerability: VulnerabilityEvidence
    assets: tuple[AssetInventoryItem, ...]
    policy: SecurityPolicy
