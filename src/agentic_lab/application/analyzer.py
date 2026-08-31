"""Application port for structured vulnerability analysis."""

from typing import Protocol

from agentic_lab.application.contracts import LLMAnalysisDraft
from agentic_lab.application.evidence import (
    AssetInventoryItem,
    VulnerabilityEvidence,
)


class VulnerabilityAnalyzer(Protocol):
    """Produce structured vulnerability analysis from evidence."""

    def analyze(
        self,
        vulnerability: VulnerabilityEvidence,
        assets: tuple[AssetInventoryItem, ...],
        feedback: str | None = None,
    ) -> LLMAnalysisDraft:
        """Analyze vulnerability applicability across assets."""
        ...
