"""Application port for structured vulnerability analysis."""

from typing import Protocol

from agentic_lab.application.contracts import LLMAnalysisDraft
from agentic_lab.application.evidence import (
    AssetInventoryItem,
    VulnerabilityEvidence,
)


class VulnerabilityAnalyzer(Protocol):
    """Produce a structured analysis from vulnerability evidence."""

    def analyze(
        self,
        vulnerability: VulnerabilityEvidence,
        assets: tuple[AssetInventoryItem, ...],
    ) -> LLMAnalysisDraft:
        """Analyze vulnerability applicability across assets."""
        ...
