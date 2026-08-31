"""EPSS domain concepts."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from agentic_lab.domain.cve import CveId
from agentic_lab.domain.evidence import EvidenceSource

_MIN_PROBABILITY = Decimal("0")
_MAX_PROBABILITY = Decimal("1")


@dataclass(frozen=True, slots=True)
class EpssObservation:
    """Represent an observed EPSS score for a CVE on a specific date."""

    cve_id: CveId
    source: EvidenceSource
    score: Decimal
    percentile: Decimal
    score_date: date

    def __post_init__(self) -> None:
        """Validate EPSS score and percentile ranges."""
        if not _MIN_PROBABILITY <= self.score <= _MAX_PROBABILITY:
            raise ValueError("EPSS score must be between 0 and 1")

        if not _MIN_PROBABILITY <= self.percentile <= _MAX_PROBABILITY:
            raise ValueError("EPSS percentile must be between 0 and 1")
