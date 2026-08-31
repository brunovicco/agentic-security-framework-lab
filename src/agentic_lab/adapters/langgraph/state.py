"""State schemas for LangGraph vulnerability-analysis workflows."""

from typing import TypedDict

from agentic_lab.adapters.fixtures.demo import (
    AssetInventoryItem,
    SecurityPolicy,
    VulnerabilityEvidence,
)
from agentic_lab.application.contracts import (
    AnalysisResult,
    AssetAssessment,
)


class AnalysisGraphInput(TypedDict):
    """Public input accepted by the vulnerability-analysis graph."""

    cve_id: str


class AnalysisGraphOutput(TypedDict):
    """Public output returned by the vulnerability-analysis graph."""

    result: AnalysisResult


class AnalysisGraphState(TypedDict, total=False):
    """Internal state shared by vulnerability-analysis graph nodes."""

    cve_id: str
    vulnerability: VulnerabilityEvidence
    assets: tuple[AssetInventoryItem, ...]
    policy: SecurityPolicy
    assessments: tuple[AssetAssessment, ...]
    requires_human_review: bool
    result: AnalysisResult
