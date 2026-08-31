"""CISA KEV domain concepts."""

from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from agentic_lab.domain.cve import CveId
from agentic_lab.domain.evidence import EvidenceSource


class RansomwareCampaignUse(StrEnum):
    """Represent CISA's ransomware campaign-use classification."""

    KNOWN = "Known"
    UNKNOWN = "Unknown"


@dataclass(frozen=True, slots=True)
class KevObservation:
    """Represent a CVE observed in the CISA KEV catalog."""

    cve_id: CveId
    source: EvidenceSource
    date_added: date
    ransomware_campaign_use: RansomwareCampaignUse
