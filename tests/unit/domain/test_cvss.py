"""Tests for CVSS domain concepts."""

from decimal import Decimal

import pytest

from agentic_lab.domain.cve import CveId
from agentic_lab.domain.cvss import CvssV4BaseObservation
from agentic_lab.domain.evidence import EvidenceSource

_VALID_VECTOR = "CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:H/SC:N/SI:N/SA:N"


def test_cvss_v4_base_observation_accepts_valid_assessment() -> None:
    """Accept a valid observed CVSS v4.0 Base assessment."""
    observation = CvssV4BaseObservation(
        cve_id=CveId(value="CVE-2026-1234"),
        source=EvidenceSource(name="NVD"),
        score=Decimal("9.8"),
        vector=_VALID_VECTOR,
    )

    assert observation.score == Decimal("9.8")
    assert observation.vector == _VALID_VECTOR


@pytest.mark.parametrize(
    "score",
    [
        Decimal("-0.1"),
        Decimal("10.1"),
    ],
)
def test_cvss_v4_base_observation_rejects_score_outside_range(
    score: Decimal,
) -> None:
    """Reject CVSS Base scores outside the inclusive zero-to-ten range."""
    with pytest.raises(
        ValueError,
        match=r"CVSS v4\.0 Base score must be between 0 and 10",
    ):
        CvssV4BaseObservation(
            cve_id=CveId(value="CVE-2026-1234"),
            source=EvidenceSource(name="NVD"),
            score=score,
            vector=_VALID_VECTOR,
        )


@pytest.mark.parametrize(
    "score",
    [
        Decimal("NaN"),
        Decimal("Infinity"),
        Decimal("-Infinity"),
    ],
)
def test_cvss_v4_base_observation_rejects_non_finite_score(
    score: Decimal,
) -> None:
    """Reject non-finite CVSS Base scores."""
    with pytest.raises(
        ValueError,
        match=r"CVSS v4\.0 Base score must be finite",
    ):
        CvssV4BaseObservation(
            cve_id=CveId(value="CVE-2026-1234"),
            source=EvidenceSource(name="NVD"),
            score=score,
            vector=_VALID_VECTOR,
        )


@pytest.mark.parametrize(
    "score",
    [
        Decimal("0"),
        Decimal("10"),
    ],
)
def test_cvss_v4_base_observation_accepts_score_boundaries(
    score: Decimal,
) -> None:
    """Accept inclusive zero and ten CVSS Base score boundaries."""
    observation = CvssV4BaseObservation(
        cve_id=CveId(value="CVE-2026-1234"),
        source=EvidenceSource(name="NVD"),
        score=score,
        vector=_VALID_VECTOR,
    )

    assert observation.score == score


def test_cvss_v4_base_observation_rejects_wrong_vector_version() -> None:
    """Reject a vector that is not explicitly CVSS v4.0."""
    with pytest.raises(
        ValueError,
        match=r"CVSS v4\.0 vector must start",
    ):
        CvssV4BaseObservation(
            cve_id=CveId(value="CVE-2026-1234"),
            source=EvidenceSource(name="NVD"),
            score=Decimal("9.8"),
            vector="CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        )


def test_cvss_v4_base_observation_rejects_padded_vector() -> None:
    """Reject surrounding whitespace in the canonical vector."""
    with pytest.raises(
        ValueError,
        match="must not contain surrounding whitespace",
    ):
        CvssV4BaseObservation(
            cve_id=CveId(value="CVE-2026-1234"),
            source=EvidenceSource(name="NVD"),
            score=Decimal("9.8"),
            vector=f"{_VALID_VECTOR} ",
        )
