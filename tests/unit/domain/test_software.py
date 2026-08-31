"""Tests for installed software domain concepts."""

import pytest

from agentic_lab.domain.software import SoftwareInstallation


def test_software_installation_represents_observed_version() -> None:
    """Represent one software version observed on an asset."""
    installation = SoftwareInstallation(
        asset_id="api-prod-01",
        product="ExampleServer",
        version="4.1",
    )

    assert installation.asset_id == "api-prod-01"
    assert installation.product == "ExampleServer"
    assert installation.version == "4.1"


@pytest.mark.parametrize(
    ("field_name", "asset_id", "product", "version"),
    [
        ("Asset identifier", "", "ExampleServer", "4.1"),
        ("Asset identifier", " api-prod-01", "ExampleServer", "4.1"),
        ("Software product", "api-prod-01", "", "4.1"),
        ("Software product", "api-prod-01", "ExampleServer ", "4.1"),
        ("Software version", "api-prod-01", "ExampleServer", ""),
        ("Software version", "api-prod-01", "ExampleServer", " 4.1"),
    ],
)
def test_software_installation_rejects_noncanonical_values(
    field_name: str,
    asset_id: str,
    product: str,
    version: str,
) -> None:
    """Reject empty or whitespace-padded installation values."""
    with pytest.raises(ValueError, match=field_name):
        SoftwareInstallation(
            asset_id=asset_id,
            product=product,
            version=version,
        )
