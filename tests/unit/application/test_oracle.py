"""Tests for the deterministic vulnerability-analysis oracle."""

from agentic_lab.adapters.fixtures.demo import (
    DEMO_CVE_ID,
    load_asset_inventory,
    load_vulnerability_evidence,
)
from agentic_lab.application.oracle import assess_assets_deterministically


def test_oracle_identifies_affected_and_fixed_assets() -> None:
    """Produce the deterministic baseline used to validate agentic outputs."""
    assessments = assess_assets_deterministically(
        vulnerability=load_vulnerability_evidence(DEMO_CVE_ID),
        assets=load_asset_inventory(),
    )

    statuses = {assessment.asset_id: assessment.status for assessment in assessments}

    assert statuses == {
        "api-prod-01": "affected",
        "api-prod-02": "not_affected",
    }
