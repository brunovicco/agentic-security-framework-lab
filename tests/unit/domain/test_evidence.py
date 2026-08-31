"""Tests for evidence domain concepts."""

import pytest

from agentic_lab.domain.evidence import EvidenceSource


def test_evidence_source_accepts_canonical_name() -> None:
    """Accept a non-empty canonical source name."""
    source = EvidenceSource(name="NVD")

    assert source.name == "NVD"


def test_evidence_source_has_value_semantics() -> None:
    """Treat sources with the same canonical name as equal values."""
    assert EvidenceSource(name="NVD") == EvidenceSource(name="NVD")


@pytest.mark.parametrize(
    "name",
    [
        "",
        " ",
        " NVD",
        "NVD ",
    ],
)
def test_evidence_source_rejects_noncanonical_name(name: str) -> None:
    """Reject empty or whitespace-padded source names."""
    with pytest.raises(ValueError):
        EvidenceSource(name=name)
