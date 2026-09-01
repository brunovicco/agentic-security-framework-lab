"""Tests for the framework-neutral adversarial evaluation fixture."""

from collections import Counter

from agentic_lab.adapters.fixtures.adversarial_evaluation import (
    ADVERSARIAL_EVALUATION_SCENARIOS,
    CONFIDENCE_SENTINEL_ADV_10,
    RECOMMENDATION_CANARY_ADV_06,
    RECOMMENDATION_CANARY_ADV_07,
    RECOMMENDATION_CANARY_ADV_08,
    load_adversarial_evaluation_scenarios,
)
from agentic_lab.adapters.fixtures.evaluation import load_evaluation_scenarios
from agentic_lab.application.analysis_prompt import SECURITY_ANALYSIS_SYSTEM_PROMPT

_EXPECTED_ADVERSARIAL_IDS = {
    "adv-01-status-goal-hijack",
    "adv-02-fake-system-authority",
    "adv-03-fake-evaluator-authority",
    "adv-04-asset-omission-pressure",
    "adv-05-duplicate-output-pressure",
    "adv-06-recommendation-canary-hijack",
    "adv-07-fake-human-approval",
    "adv-08-fake-policy-override",
    "adv-09-unknown-version-guess-pressure",
    "adv-10-confidence-sentinel-pressure",
}

_EXPECTED_BASELINE_IDS = {
    "baseline-mixed",
    "product-mismatch",
    "unknown-version",
    "fixed-boundary",
    "adversarial-asset-id",
}


def test_adversarial_dataset_contains_exactly_ten_unique_scenarios() -> None:
    scenarios = load_adversarial_evaluation_scenarios()
    scenario_ids = [scenario.scenario_id for scenario in scenarios]

    assert scenarios == ADVERSARIAL_EVALUATION_SCENARIOS
    assert len(scenarios) == 10
    assert len(scenario_ids) == len(set(scenario_ids))
    assert set(scenario_ids) == _EXPECTED_ADVERSARIAL_IDS


def test_adversarial_expected_asset_identity_matches_supplied_assets() -> None:
    for scenario in load_adversarial_evaluation_scenarios():
        supplied_ids = Counter(asset["asset_id"] for asset in scenario.assets)
        expected_ids = Counter(asset.asset_id for asset in scenario.expected_assets)

        assert supplied_ids == expected_ids, scenario.scenario_id


def test_adversarial_cve_ids_are_unique() -> None:
    cve_ids = [
        scenario.vulnerability["cve_id"]
        for scenario in load_adversarial_evaluation_scenarios()
    ]

    assert len(cve_ids) == len(set(cve_ids))


def test_recommendation_canaries_are_unique_and_absent_from_trusted_prompt() -> None:
    canaries = (
        RECOMMENDATION_CANARY_ADV_06,
        RECOMMENDATION_CANARY_ADV_07,
        RECOMMENDATION_CANARY_ADV_08,
    )

    assert len(canaries) == len(set(canaries))
    for canary in canaries:
        assert canary not in SECURITY_ANALYSIS_SYSTEM_PROMPT


def test_recommendation_canaries_are_bound_to_only_one_scenario_each() -> None:
    scenarios = load_adversarial_evaluation_scenarios()

    for canary in (
        RECOMMENDATION_CANARY_ADV_06,
        RECOMMENDATION_CANARY_ADV_07,
        RECOMMENDATION_CANARY_ADV_08,
    ):
        matching = [
            scenario
            for scenario in scenarios
            if scenario.security.forbidden_recommendation_canary == canary
        ]
        assert len(matching) == 1
        assert canary in matching[0].assets[0]["asset_id"]


def test_confidence_sentinel_is_bound_only_to_adv_10() -> None:
    matching = [
        scenario
        for scenario in load_adversarial_evaluation_scenarios()
        if scenario.security.forbidden_confidence_value == CONFIDENCE_SENTINEL_ADV_10
    ]

    assert len(matching) == 1
    assert matching[0].scenario_id == "adv-10-confidence-sentinel-pressure"
    assert "0.12345" in matching[0].assets[0]["asset_id"]


def test_historical_baseline_dataset_remains_unchanged() -> None:
    scenarios = load_evaluation_scenarios()

    assert len(scenarios) == 5
    assert {scenario.scenario_id for scenario in scenarios} == _EXPECTED_BASELINE_IDS


def test_every_adversarial_scenario_is_tagged_as_adversarial() -> None:
    for scenario in load_adversarial_evaluation_scenarios():
        assert "adversarial" in scenario.tags
