"""CVSS domain concepts."""

from dataclasses import dataclass
from decimal import Decimal

from agentic_lab.domain.cve import CveId
from agentic_lab.domain.evidence import EvidenceSource

_MIN_CVSS_SCORE = Decimal("0")
_MAX_CVSS_SCORE = Decimal("10")
_CVSS_V4_VECTOR_PREFIX = "CVSS:4.0/"


@dataclass(frozen=True, slots=True)
class CvssV4BaseObservation:
    """Represent an observed CVSS v4.0 Base assessment for a CVE."""

    cve_id: CveId
    source: EvidenceSource
    score: Decimal
    vector: str

    def __post_init__(self) -> None:
        """Validate the observed CVSS v4.0 Base assessment."""
        if not self.score.is_finite():
            raise ValueError("CVSS v4.0 Base score must be finite")

        if not _MIN_CVSS_SCORE <= self.score <= _MAX_CVSS_SCORE:
            raise ValueError("CVSS v4.0 Base score must be between 0 and 10")

        if not self.vector.startswith(_CVSS_V4_VECTOR_PREFIX):
            raise ValueError("CVSS v4.0 vector must start with 'CVSS:4.0/'")

        if self.vector != self.vector.strip():
            raise ValueError("CVSS v4.0 vector must not contain surrounding whitespace")
