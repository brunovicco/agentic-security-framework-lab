"""Tests for CVE domain concepts."""

import pytest

from agentic_lab.domain.cve import CveId


def test_cve_id_accepts_canonical_identifier() -> None:
    """Accept a canonical CVE identifier."""
    cve_id = CveId(value="CVE-2026-1234")

    assert cve_id.value == "CVE-2026-1234"


def test_cve_id_accepts_long_sequence_number() -> None:
    """Do not impose an external record-format length limit on the domain."""
    value = "CVE-2026-12345678901234567890"

    cve_id = CveId(value=value)

    assert cve_id.value == value


@pytest.mark.parametrize(
    "value",
    [
        "CVE-2026-123",
        "CVE-26-1234",
        "cve-2026-1234",
        "CVE-2026-1234 ",
        "2026-1234",
    ],
)
def test_cve_id_rejects_noncanonical_identifier(value: str) -> None:
    """Reject identifiers that do not use canonical CVE syntax."""
    with pytest.raises(ValueError, match="Invalid CVE identifier"):
        CveId(value=value)
