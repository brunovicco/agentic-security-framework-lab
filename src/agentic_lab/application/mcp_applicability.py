"""Framework-neutral application contract for deterministic applicability tools."""

from pydantic import BaseModel, ConfigDict, Field, field_validator

from agentic_lab.application.contracts import AssetAssessment, Severity
from agentic_lab.application.evidence import AssetInventoryItem, VulnerabilityEvidence
from agentic_lab.application.oracle import assess_assets_deterministically
from agentic_lab.domain.cve import CveId


class VulnerabilityApplicabilityInput(BaseModel):
    """Validate vulnerability evidence accepted by the applicability tool boundary."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    cve_id: str
    product: str = Field(min_length=1)
    affected_before: str = Field(min_length=1)
    severity: Severity
    cvss_score: str = Field(min_length=1)
    epss_score: str = Field(min_length=1)
    kev_listed: bool

    @field_validator("cve_id")
    @classmethod
    def validate_cve_id(cls, value: str) -> str:
        """Require a canonical CVE identifier."""
        return CveId(value=value).value


class AssetApplicabilityInput(BaseModel):
    """Validate one asset passed to the deterministic applicability tool."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    asset_id: str = Field(min_length=1)
    product: str = Field(min_length=1)
    version: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    network_exposure: str = Field(min_length=1)


class ApplicabilityAssessmentResult(BaseModel):
    """Return deterministic applicability without LLM or policy side effects."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    cve_id: str
    assessments: tuple[AssetAssessment, ...]


class ApplicabilityContractDescription(BaseModel):
    """Describe the application-owned schemas exposed as MCP contract context."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    contract: str
    vulnerability_input_schema: dict[str, object]
    asset_input_schema: dict[str, object]
    result_schema: dict[str, object]


def describe_applicability_contract() -> ApplicabilityContractDescription:
    """Build contract metadata from the authoritative Pydantic application models."""
    return ApplicabilityContractDescription(
        contract="assess_vulnerability_applicability",
        vulnerability_input_schema=VulnerabilityApplicabilityInput.model_json_schema(),
        asset_input_schema=AssetApplicabilityInput.model_json_schema(),
        result_schema=ApplicabilityAssessmentResult.model_json_schema(),
    )


def assess_vulnerability_applicability(
    vulnerability: VulnerabilityApplicabilityInput,
    assets: tuple[AssetApplicabilityInput, ...],
) -> ApplicabilityAssessmentResult:
    """Assess supplied assets using the existing deterministic application oracle."""
    vulnerability_evidence: VulnerabilityEvidence = {
        "cve_id": vulnerability.cve_id,
        "product": vulnerability.product,
        "affected_before": vulnerability.affected_before,
        "severity": vulnerability.severity,
        "cvss_score": vulnerability.cvss_score,
        "epss_score": vulnerability.epss_score,
        "kev_listed": vulnerability.kev_listed,
    }
    asset_evidence: tuple[AssetInventoryItem, ...] = tuple(
        {
            "asset_id": asset.asset_id,
            "product": asset.product,
            "version": asset.version,
            "environment": asset.environment,
            "network_exposure": asset.network_exposure,
        }
        for asset in assets
    )
    assessments = assess_assets_deterministically(
        vulnerability=vulnerability_evidence,
        assets=asset_evidence,
    )
    return ApplicabilityAssessmentResult(
        cve_id=vulnerability.cve_id,
        assessments=assessments,
    )
