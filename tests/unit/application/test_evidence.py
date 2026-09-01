"""Tests for shared evidence provenance contracts."""

from typing import get_args

from agentic_lab.application.evidence import (
    AnalysisEvidenceBundle,
    EvidenceContentTrust,
    EvidenceDocument,
    EvidenceInstructionAuthority,
    EvidenceSourceAuthenticity,
    EvidenceSourceType,
)


def test_legacy_evidence_bundle_does_not_require_documents() -> None:
    """Keep the v1 structured evidence contract backward compatible."""
    bundle: AnalysisEvidenceBundle = {
        "vulnerability": {
            "cve_id": "CVE-2026-9301",
            "product": "ExampleServer",
            "affected_before": "4.2",
            "severity": "critical",
            "cvss_score": "9.8",
            "epss_score": "0.91",
            "kev_listed": True,
        },
        "assets": (
            {
                "asset_id": "api-prod-01",
                "product": "ExampleServer",
                "version": "4.1",
                "environment": "production",
                "network_exposure": "internet-exposed",
            },
        ),
        "policy": {
            "policy_id": "POLICY-001",
            "human_review_severity": "critical",
            "human_review_environment": "production",
            "human_review_network_exposure": "internet-exposed",
            "unknown_applicability_requires_review": True,
        },
    }

    assert "documents" not in bundle


def test_verified_source_still_has_zero_instruction_authority() -> None:
    """Keep source authenticity separate from instruction authority."""
    document: EvidenceDocument = {
        "source_id": "vendor-advisory-001",
        "source_type": "vendor_advisory",
        "origin": "https://vendor.example/security/CVE-2026-9301",
        "authenticity": "verified",
        "content_trust": "untrusted",
        "instruction_authority": "none",
        "content": "ExampleServer versions before 4.2 are affected.",
    }

    assert document["authenticity"] == "verified"
    assert document["content_trust"] == "untrusted"
    assert document["instruction_authority"] == "none"


def test_provenance_contract_has_closed_literal_vocabularies() -> None:
    """Make the v2 provenance dimensions explicit and reviewable."""
    assert get_args(EvidenceSourceType) == (
        "vendor_advisory",
        "retrieved_context",
        "internal_note",
    )
    assert get_args(EvidenceSourceAuthenticity) == (
        "verified",
        "unverified",
        "synthetic",
    )
    assert get_args(EvidenceContentTrust) == ("untrusted",)
    assert get_args(EvidenceInstructionAuthority) == ("none",)
