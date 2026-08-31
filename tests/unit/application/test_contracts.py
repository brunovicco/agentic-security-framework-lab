"""Tests for shared agentic application contracts."""

import pytest
from pydantic import ValidationError

from agentic_lab.application.contracts import (
    AnalysisRequest,
    AnalysisResult,
    AssetAssessment,
)


def test_analysis_request_accepts_canonical_cve() -> None:
    """Accept a canonical CVE identifier."""
    request = AnalysisRequest(cve_id="CVE-2026-1234")

    assert request.cve_id == "CVE-2026-1234"


def test_analysis_request_rejects_invalid_cve() -> None:
    """Reject an invalid CVE identifier."""
    with pytest.raises(ValidationError):
        AnalysisRequest(cve_id="invalid")


def test_analysis_result_accepts_valid_contract() -> None:
    """Accept a framework-independent analysis result."""
    result = AnalysisResult(
        cve_id="CVE-2026-1234",
        severity="critical",
        assets=(
            AssetAssessment(
                asset_id="api-prod-01",
                status="affected",
                rationale="Installed version 4.1 is below fixed version 4.2.",
            ),
        ),
        recommendation="Prioritize remediation.",
        confidence=0.95,
        evidence=("fixture:vulnerability", "fixture:inventory"),
        requires_human_review=True,
    )

    assert result.confidence == 0.95
    assert result.assets[0].status == "affected"


def test_analysis_result_rejects_invalid_confidence() -> None:
    """Reject confidence values outside zero-to-one bounds."""
    with pytest.raises(ValidationError):
        AnalysisResult(
            cve_id="CVE-2026-1234",
            severity="critical",
            assets=(),
            recommendation="Review.",
            confidence=1.1,
            evidence=(),
            requires_human_review=True,
        )
