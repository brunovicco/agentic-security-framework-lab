"""Tests for the deterministic agentic demo fixture."""

import pytest

from agentic_lab.adapters.fixtures.demo import (
    DEMO_CVE_ID,
    load_asset_inventory,
    load_security_policy,
    load_vulnerability_evidence,
)


def test_demo_vulnerability_contains_expected_affected_range() -> None:
    """Expose the deterministic vulnerability rule used by every framework."""
    evidence = load_vulnerability_evidence(DEMO_CVE_ID)

    assert evidence["product"] == "ExampleServer"
    assert evidence["affected_before"] == "4.2"


def test_demo_vulnerability_rejects_unknown_cve() -> None:
    """Reject CVEs outside the deterministic demo dataset."""
    with pytest.raises(KeyError, match="Unknown demo CVE"):
        load_vulnerability_evidence("CVE-2026-9999")


def test_demo_inventory_contains_affected_and_fixed_versions() -> None:
    """Provide one affected and one fixed software installation."""
    assets = load_asset_inventory()

    assert assets[0]["version"] == "4.1"
    assert assets[1]["version"] == "4.4"


def test_demo_policy_requires_review_for_unknown_applicability() -> None:
    """Preserve the demo fail-closed human-review policy."""
    policy = load_security_policy()

    assert policy["unknown_applicability_requires_review"]
