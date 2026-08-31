"""Software version comparison domain concepts."""

import re
from dataclasses import dataclass
from typing import Self

_MAJOR_MINOR_PATTERN = re.compile(r"(?P<major>0|[1-9][0-9]*)\.(?P<minor>0|[1-9][0-9]*)")


@dataclass(frozen=True, slots=True, order=True)
class MajorMinorVersion:
    """Represent a comparable canonical major.minor software version."""

    major: int
    minor: int

    def __post_init__(self) -> None:
        """Validate numeric version components."""
        if self.major < 0 or self.minor < 0:
            raise ValueError("Version components must not be negative")

    @classmethod
    def parse(cls, value: str) -> Self:
        """Parse a canonical major.minor version string."""
        match = _MAJOR_MINOR_PATTERN.fullmatch(value)

        if match is None:
            raise ValueError(f"Invalid major.minor version: {value!r}")

        return cls(
            major=int(match.group("major")),
            minor=int(match.group("minor")),
        )

    def __str__(self) -> str:
        """Return the canonical major.minor representation."""
        return f"{self.major}.{self.minor}"
