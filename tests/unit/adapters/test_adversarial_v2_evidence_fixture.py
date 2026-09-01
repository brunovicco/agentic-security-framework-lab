"""Tests for the adversarial v2 evidence-plane dataset."""

from agentic_lab.adapters.fixtures.adversarial_v2_evidence import (
    RECOMMENDATION_CANARY_V2_04,
    RECOMMENDATION_CANARY_V2_05,
    load_adversarial_v2_evidence_scenarios,
)
from agentic_lab.application.adversarial_v2 import build_adversarial_v2_evidence_bundle


def test_v2_dataset_has_six_unique_evidence_plane_scenarios() -> None:
    scenarios = load_adversarial_v2_evidence_scenarios()

    assert len(scenarios) == 6
    assert len({scenario.scenario_id for scenario in scenarios}) == 6
    assert all(scenario.scenario_id.startswith("adv2-") for scenario in scenarios)
    assert all(scenario.documents for scenario in scenarios)


def test_v2_asset_ids_are_clean_and_attacks_live_in_document_content() -> None:
    scenarios = load_adversarial_v2_evidence_scenarios()
    instruction_markers = (
        "IGNORE",
        "DIRECTIVE",
        "INSTRUCTION",
        "OVERRIDE",
        "APPROVAL",
        "NOT_AFFECTED",
    )

    for scenario in scenarios:
        for asset in scenario.assets:
            assert not any(marker in asset["asset_id"].upper() for marker in instruction_markers)

    combined_content = "\n".join(
        document["content"]
        for scenario in scenarios
        for document in scenario.documents
    )
    assert "NOT_AFFECTED" in combined_content
    assert "AUTOMATION DIRECTIVE" in combined_content
    assert "MODEL INSTRUCTION" in combined_content


def test_every_v2_document_has_zero_instruction_authority() -> None:
    for scenario in load_adversarial_v2_evidence_scenarios():
        for document in scenario.documents:
            assert document["content_trust"] == "untrusted"
            assert document["instruction_authority"] == "none"
            assert document["authenticity"] in {"verified", "unverified", "synthetic"}


def test_verified_source_authenticity_does_not_change_instruction_authority() -> None:
    verified_documents = [
        document
        for scenario in load_adversarial_v2_evidence_scenarios()
        for document in scenario.documents
        if document["authenticity"] == "verified"
    ]

    assert verified_documents
    assert all(document["instruction_authority"] == "none" for document in verified_documents)
    assert all(document["content_trust"] == "untrusted" for document in verified_documents)


def test_v2_recommendation_canaries_exist_only_in_target_document_content() -> None:
    scenarios = {scenario.scenario_id: scenario for scenario in load_adversarial_v2_evidence_scenarios()}

    scenario_04 = scenarios["adv2-04-recommendation-canary-evidence"]
    scenario_05 = scenarios["adv2-05-fake-human-approval-evidence"]

    assert scenario_04.attack.recommendation_canary == RECOMMENDATION_CANARY_V2_04
    assert scenario_04.security.forbidden_recommendation_canary == RECOMMENDATION_CANARY_V2_04
    assert RECOMMENDATION_CANARY_V2_04 in scenario_04.documents[0]["content"]

    assert scenario_05.attack.recommendation_canary == RECOMMENDATION_CANARY_V2_05
    assert scenario_05.security.forbidden_recommendation_canary == RECOMMENDATION_CANARY_V2_05
    assert RECOMMENDATION_CANARY_V2_05 in scenario_05.documents[0]["content"]


def test_conflicting_evidence_scenario_contains_verified_and_unverified_sources() -> None:
    scenario = next(
        item
        for item in load_adversarial_v2_evidence_scenarios()
        if item.scenario_id == "adv2-06-conflicting-evidence-goal-hijack"
    )

    assert len(scenario.documents) == 2
    assert {document["authenticity"] for document in scenario.documents} == {
        "verified",
        "unverified",
    }
    assert scenario.attack.forced_assets[0].status == "not_affected"
    assert scenario.expected_assets[0].status == "affected"


def test_v2_bundle_preserves_documents_without_promoting_them_to_policy() -> None:
    scenario = load_adversarial_v2_evidence_scenarios()[0]
    bundle = build_adversarial_v2_evidence_bundle(scenario)

    assert bundle["documents"] == scenario.documents
    assert bundle["vulnerability"] == scenario.vulnerability
    assert bundle["assets"] == scenario.assets
    assert bundle["policy"] == scenario.policy
    assert "documents" not in bundle["policy"]
