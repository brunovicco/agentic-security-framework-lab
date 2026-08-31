"""Tests for asset inventory domain concepts."""

import pytest

from agentic_lab.domain.asset import (
    Asset,
    DeploymentEnvironment,
    NetworkExposure,
)


def test_asset_represents_production_internet_exposure() -> None:
    """Represent a production asset explicitly observed as internet exposed."""
    asset = Asset(
        asset_id="api-prod-01",
        environment=DeploymentEnvironment.PRODUCTION,
        network_exposure=NetworkExposure.INTERNET_EXPOSED,
    )

    assert asset.asset_id == "api-prod-01"
    assert asset.environment is DeploymentEnvironment.PRODUCTION
    assert asset.network_exposure is NetworkExposure.INTERNET_EXPOSED


def test_asset_preserves_unknown_environment() -> None:
    """Preserve missing deployment classification as unknown."""
    asset = Asset(
        asset_id="asset-01",
        environment=DeploymentEnvironment.UNKNOWN,
        network_exposure=NetworkExposure.INTERNAL,
    )

    assert asset.environment is DeploymentEnvironment.UNKNOWN


def test_asset_preserves_unknown_network_exposure() -> None:
    """Preserve missing network-exposure evidence as unknown."""
    asset = Asset(
        asset_id="asset-01",
        environment=DeploymentEnvironment.PRODUCTION,
        network_exposure=NetworkExposure.UNKNOWN,
    )

    assert asset.network_exposure is NetworkExposure.UNKNOWN


@pytest.mark.parametrize(
    "asset_id",
    [
        "",
        " ",
        " api-prod-01",
        "api-prod-01 ",
    ],
)
def test_asset_rejects_noncanonical_identifier(asset_id: str) -> None:
    """Reject empty or whitespace-padded asset identifiers."""
    with pytest.raises(ValueError, match="Asset identifier"):
        Asset(
            asset_id=asset_id,
            environment=DeploymentEnvironment.PRODUCTION,
            network_exposure=NetworkExposure.INTERNAL,
        )
