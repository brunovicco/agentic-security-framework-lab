"""Evidence domain concepts."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EvidenceSource:
    """Identify the declared source of observed evidence."""

    name: str

    def __post_init__(self) -> None:
        """Validate the canonical source name."""
        if not self.name:
            raise ValueError("Evidence source name must not be empty")

        if self.name != self.name.strip():
            raise ValueError("Evidence source name must not contain surrounding whitespace")
