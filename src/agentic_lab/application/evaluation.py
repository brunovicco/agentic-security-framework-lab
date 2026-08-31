"""Shared contracts for vulnerability-analysis evaluation scenarios."""

from dataclasses import dataclass

from agentic_lab.application.contracts import ApplicabilityStatus
from agentic_lab.application.evidence import (
    AssetInventoryItem,
    SecurityPolicy,
    VulnerabilityEvidence,
)


@dataclass(frozen=True, slots=True)
class ExpectedAssetStatus:
    """Represent the expected applicability status for one asset."""

    asset_id: str
    status: ApplicabilityStatus


@dataclass(frozen=True, slots=True)
class EvaluationScenario:
    """Represent one framework-neutral evaluation scenario."""

    scenario_id: str
    description: str
    vulnerability: VulnerabilityEvidence
    assets: tuple[AssetInventoryItem, ...]
    policy: SecurityPolicy
    expected_assets: tuple[ExpectedAssetStatus, ...]
    tags: tuple[str, ...]
