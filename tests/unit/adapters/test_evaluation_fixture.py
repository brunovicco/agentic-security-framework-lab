"""Tests for the shared vulnerability-analysis evaluation dataset."""

from agentic_lab.adapters.fixtures.evaluation import (
    load_evaluation_scenarios,
)
from agentic_lab.application.oracle import (
    assess_assets_deterministically,
)


def test_evaluation_scenario_ids_are_unique() -> None:
    """Require stable unique identifiers for benchmark scenarios."""
    scenarios = load_evaluation_scenarios()

    scenario_ids = [scenario.scenario_id for scenario in scenarios]

    assert len(scenario_ids) == len(set(scenario_ids))


def test_evaluation_scenarios_match_deterministic_oracle() -> None:
    """Require expected statuses to agree with deterministic ground truth."""
    scenarios = load_evaluation_scenarios()

    for scenario in scenarios:
        observed_assessments = assess_assets_deterministically(
            vulnerability=scenario.vulnerability,
            assets=scenario.assets,
        )

        observed = {assessment.asset_id: assessment.status for assessment in observed_assessments}

        expected = {
            assessment.asset_id: assessment.status for assessment in scenario.expected_assets
        }

        assert observed == expected, scenario.scenario_id


def test_evaluation_dataset_covers_core_applicability_states() -> None:
    """Cover all applicability outcomes needed by the first benchmark."""
    scenarios = load_evaluation_scenarios()

    statuses = {
        assessment.status for scenario in scenarios for assessment in scenario.expected_assets
    }

    assert {
        "affected",
        "not_affected",
        "not_applicable",
        "unknown",
    } <= statuses


def test_evaluation_dataset_contains_adversarial_scenario() -> None:
    """Keep at least one instruction-data-boundary security case."""
    scenarios = load_evaluation_scenarios()

    adversarial = [scenario for scenario in scenarios if "adversarial" in scenario.tags]

    assert len(adversarial) == 1
    assert "prompt-injection" in adversarial[0].tags
