"""Tests for EPSS domain concepts."""

from datetime import date
from decimal import Decimal

import pytest

from agentic_lab.domain.cve import CveId
from agentic_lab.domain.epss import EpssObservation
from agentic_lab.domain.evidence import EvidenceSource


def test_epss_observation_accepts_valid_values() -> None:
    """Accept an EPSS observation with valid probability values."""
    observation = EpssObservation(
        cve_id=CveId(value="CVE-2026-1234"),
        source=EvidenceSource(name="FIRST EPSS"),
        score=Decimal("0.913420000"),
        percentile=Decimal("0.987650000"),
        score_date=date(2026, 8, 30),
    )

    assert observation.score == Decimal("0.913420000")
    assert observation.percentile == Decimal("0.987650000")


@pytest.mark.parametrize(
    "score",
    [
        Decimal("-0.0001"),
        Decimal("1.0001"),
    ],
)
def test_epss_observation_rejects_score_outside_probability_range(
    score: Decimal,
) -> None:
    """Reject an EPSS score outside the inclusive zero-to-one range."""
    with pytest.raises(ValueError, match="EPSS score must be between 0 and 1"):
        EpssObservation(
            cve_id=CveId(value="CVE-2026-1234"),
            source=EvidenceSource(name="FIRST EPSS"),
            score=score,
            percentile=Decimal("0.50"),
            score_date=date(2026, 8, 30),
        )


@pytest.mark.parametrize(
    "percentile",
    [
        Decimal("-0.0001"),
        Decimal("1.0001"),
    ],
)
def test_epss_observation_rejects_percentile_outside_probability_range(
    percentile: Decimal,
) -> None:
    """Reject an EPSS percentile outside the inclusive zero-to-one range."""
    with pytest.raises(ValueError, match="EPSS percentile must be between 0 and 1"):
        EpssObservation(
            cve_id=CveId(value="CVE-2026-1234"),
            source=EvidenceSource(name="FIRST EPSS"),
            score=Decimal("0.50"),
            percentile=percentile,
            score_date=date(2026, 8, 30),
        )


@pytest.mark.parametrize(
    ("score", "percentile"),
    [
        (Decimal("0"), Decimal("0")),
        (Decimal("1"), Decimal("1")),
    ],
)
def test_epss_observation_accepts_probability_boundaries(
    score: Decimal,
    percentile: Decimal,
) -> None:
    """Accept inclusive zero and one probability boundaries."""
    observation = EpssObservation(
        cve_id=CveId(value="CVE-2026-1234"),
        source=EvidenceSource(name="FIRST EPSS"),
        score=score,
        percentile=percentile,
        score_date=date(2026, 8, 30),
    )

    assert observation.score == score
    assert observation.percentile == percentile
