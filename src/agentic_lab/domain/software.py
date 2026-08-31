"""Installed software domain concepts."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SoftwareInstallation:
    """Represent one observed software installation on an asset."""

    asset_id: str
    product: str
    version: str

    def __post_init__(self) -> None:
        """Validate canonical software installation values."""
        self._require_canonical_text(self.asset_id, "Asset identifier")
        self._require_canonical_text(self.product, "Software product")
        self._require_canonical_text(self.version, "Software version")

    @staticmethod
    def _require_canonical_text(value: str, field_name: str) -> None:
        """Require non-empty text without surrounding whitespace."""
        if not value:
            raise ValueError(f"{field_name} must not be empty")

        if value != value.strip():
            raise ValueError(f"{field_name} must not contain surrounding whitespace")
