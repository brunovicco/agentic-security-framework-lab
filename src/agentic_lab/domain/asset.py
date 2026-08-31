"""Asset inventory domain concepts."""

from dataclasses import dataclass
from enum import StrEnum


class DeploymentEnvironment(StrEnum):
    """Represent the deployment environment of an asset."""

    PRODUCTION = "production"
    NON_PRODUCTION = "non-production"
    UNKNOWN = "unknown"


class NetworkExposure(StrEnum):
    """Represent observed network exposure for an asset."""

    INTERNET_EXPOSED = "internet-exposed"
    INTERNAL = "internal"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class Asset:
    """Represent an identified asset in the environment."""

    asset_id: str
    environment: DeploymentEnvironment
    network_exposure: NetworkExposure

    def __post_init__(self) -> None:
        """Validate the canonical asset identifier."""
        if not self.asset_id:
            raise ValueError("Asset identifier must not be empty")

        if self.asset_id != self.asset_id.strip():
            raise ValueError("Asset identifier must not contain surrounding whitespace")
