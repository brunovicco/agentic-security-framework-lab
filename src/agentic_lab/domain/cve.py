"""CVE domain concepts."""

import re
from dataclasses import dataclass

_CVE_ID_PATTERN = re.compile(r"CVE-[0-9]{4}-[0-9]{4,}")


@dataclass(frozen=True, slots=True)
class CveId:
    """Represent a canonical CVE identifier."""

    value: str

    def __post_init__(self) -> None:
        """Validate the identifier after initialization."""
        if _CVE_ID_PATTERN.fullmatch(self.value) is None:
            raise ValueError(f"Invalid CVE identifier: {self.value!r}")
