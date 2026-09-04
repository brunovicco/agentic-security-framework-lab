"""Tests for the framework-neutral deterministic MCP applicability contract."""

import pytest
from pydantic import ValidationError

from agentic_lab.application.mcp_applicability import (
    AssetApplicabilityInput,
    VulnerabilityApplicabilityInput,
    assess_vulnerability_applicability,
)


def _vulnerability() -> VulnerabilityApplicabilityInput:
    return VulnerabilityApplicabilityInput(
        cve_id="CVE-2026-9001",
        product="ExampleServer",
        affected_before="4.2",
        severity="critical",
        cvss_score="9.8",
        epss_score="0.91",
        kev_listed=True,
    )


def _asset(
    *,
    asset_id: str,
    product: str = "ExampleServer",
    version: str = "4.1",
) -> AssetApplicabilityInput:
    return AssetApplicabilityInput(
        asset_id=asset_id,
        product=product,
        version=version,
        environment="production",
        network_exposure="internet-exposed",
    )


def test_assess_vulnerability_applicability_reuses_deterministic_oracle() -> None:
    result = assess_vulnerability_applicability(
        vulnerability=_vulnerability(),
        assets=(
            _asset(asset_id="affected", version="4.1"),
            _asset(asset_id="fixed", version="4.2"),
            _asset(asset_id="other-product", product="OtherServer"),
            _asset(asset_id="unknown-version", version="not-a-version"),
        ),
    )

    assert result.cve_id == "CVE-2026-9001"
    assert [(item.asset_id, item.status) for item in result.assessments] == [
        ("affected", "affected"),
        ("fixed", "not_affected"),
        ("other-product", "not_applicable"),
        ("unknown-version", "unknown"),
    ]


def test_assess_vulnerability_applicability_is_repeatable_for_same_inputs() -> None:
    vulnerability = _vulnerability()
    assets = (_asset(asset_id="api-prod-01"),)

    first = assess_vulnerability_applicability(vulnerability=vulnerability, assets=assets)
    second = assess_vulnerability_applicability(vulnerability=vulnerability, assets=assets)

    assert first == second


def test_vulnerability_input_rejects_non_canonical_cve() -> None:
    with pytest.raises(ValidationError):
        VulnerabilityApplicabilityInput(
            cve_id="not-a-cve",
            product="ExampleServer",
            affected_before="4.2",
            severity="critical",
            cvss_score="9.8",
            epss_score="0.91",
            kev_listed=True,
        )
