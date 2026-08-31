"""Tests for software version comparison domain concepts."""

import pytest

from agentic_lab.domain.versioning import MajorMinorVersion


def test_major_minor_version_parses_canonical_value() -> None:
    """Parse a canonical major.minor software version."""
    version = MajorMinorVersion.parse("4.1")

    assert version.major == 4
    assert version.minor == 1
    assert str(version) == "4.1"


def test_major_minor_version_compares_minor_numerically() -> None:
    """Compare minor components numerically rather than lexicographically."""
    version_4_10 = MajorMinorVersion.parse("4.10")
    version_4_2 = MajorMinorVersion.parse("4.2")

    assert version_4_10 > version_4_2


def test_major_minor_version_compares_major_before_minor() -> None:
    """Compare the major component before the minor component."""
    version_5_0 = MajorMinorVersion.parse("5.0")
    version_4_999 = MajorMinorVersion.parse("4.999")

    assert version_5_0 > version_4_999


def test_major_minor_version_supports_equality() -> None:
    """Treat equal major and minor components as the same value."""
    assert MajorMinorVersion.parse("4.2") == MajorMinorVersion.parse("4.2")


@pytest.mark.parametrize(
    "value",
    [
        "",
        "4",
        "4.1.0",
        "v4.1",
        "04.1",
        "4.01",
        " 4.1",
        "4.1 ",
    ],
)
def test_major_minor_version_rejects_unsupported_syntax(value: str) -> None:
    """Reject values outside the canonical major.minor version scheme."""
    with pytest.raises(ValueError, match=r"Invalid major\.minor version"):
        MajorMinorVersion.parse(value)


def test_major_minor_version_rejects_negative_components() -> None:
    """Reject negative components when constructed directly."""
    with pytest.raises(ValueError, match="must not be negative"):
        MajorMinorVersion(major=4, minor=-1)
