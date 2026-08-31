"""Tests for CISA KEV domain concepts."""

from datetime import date

from agentic_lab.domain.cve import CveId
from agentic_lab.domain.evidence import EvidenceSource
from agentic_lab.domain.kev import KevObservation, RansomwareCampaignUse


def test_kev_observation_represents_known_exploitation() -> None:
    """Represent a CVE observed in the CISA KEV catalog."""
    observation = KevObservation(
        cve_id=CveId(value="CVE-2024-40766"),
        source=EvidenceSource(name="CISA KEV"),
        date_added=date(2024, 9, 9),
        ransomware_campaign_use=RansomwareCampaignUse.KNOWN,
    )

    assert observation.cve_id == CveId(value="CVE-2024-40766")
    assert observation.date_added == date(2024, 9, 9)


def test_kev_observation_preserves_known_ransomware_classification() -> None:
    """Preserve CISA's Known ransomware-use classification."""
    observation = KevObservation(
        cve_id=CveId(value="CVE-2024-40766"),
        source=EvidenceSource(name="CISA KEV"),
        date_added=date(2024, 9, 9),
        ransomware_campaign_use=RansomwareCampaignUse.KNOWN,
    )

    assert observation.ransomware_campaign_use is RansomwareCampaignUse.KNOWN


def test_kev_observation_preserves_unknown_ransomware_classification() -> None:
    """Preserve CISA's Unknown ransomware-use classification."""
    observation = KevObservation(
        cve_id=CveId(value="CVE-2024-35250"),
        source=EvidenceSource(name="CISA KEV"),
        date_added=date(2025, 1, 14),
        ransomware_campaign_use=RansomwareCampaignUse.UNKNOWN,
    )

    assert observation.ransomware_campaign_use is RansomwareCampaignUse.UNKNOWN
