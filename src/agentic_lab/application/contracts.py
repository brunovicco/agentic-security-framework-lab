"""Shared application contracts for agentic vulnerability analysis."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from agentic_lab.domain.cve import CveId

ApplicabilityStatus = Literal[
    "affected",
    "not_affected",
    "not_applicable",
    "unknown",
]

Severity = Literal[
    "critical",
    "high",
    "medium",
    "low",
    "unknown",
]


def _validate_cve_id(value: str) -> str:
    """Return a canonical CVE identifier or raise ValueError."""
    return CveId(value=value).value


class AnalysisRequest(BaseModel):
    """Request shared by every framework implementation."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    cve_id: str

    @field_validator("cve_id")
    @classmethod
    def validate_cve_id(cls, value: str) -> str:
        """Require a canonical CVE identifier."""
        return _validate_cve_id(value)


class AssetAssessment(BaseModel):
    """Represent one framework's assessment for an asset."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    asset_id: str = Field(min_length=1)
    status: ApplicabilityStatus
    rationale: str = Field(min_length=1)


class AnalysisResult(BaseModel):
    """Result contract shared by every framework implementation."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    cve_id: str
    severity: Severity
    assets: tuple[AssetAssessment, ...]
    recommendation: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: tuple[str, ...]
    requires_human_review: bool

    @field_validator("cve_id")
    @classmethod
    def validate_cve_id(cls, value: str) -> str:
        """Require a canonical CVE identifier."""
        return _validate_cve_id(value)
