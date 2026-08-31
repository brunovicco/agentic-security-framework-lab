"""Deterministic oracle for vulnerability applicability."""

from agentic_lab.application.contracts import (
    ApplicabilityStatus,
    AssetAssessment,
)
from agentic_lab.application.evidence import (
    AssetInventoryItem,
    VulnerabilityEvidence,
)
from agentic_lab.domain.versioning import MajorMinorVersion
from agentic_lab.domain.vulnerability import AffectedBeforeVersionRule


def assess_assets_deterministically(
    vulnerability: VulnerabilityEvidence,
    assets: tuple[AssetInventoryItem, ...],
) -> tuple[AssetAssessment, ...]:
    """Calculate expected asset applicability without an LLM."""
    affected_versions = AffectedBeforeVersionRule(
        upper_bound_exclusive=MajorMinorVersion.parse(vulnerability["affected_before"])
    )

    assessments: list[AssetAssessment] = []

    for asset in assets:
        status: ApplicabilityStatus

        if asset["product"] != vulnerability["product"]:
            status = "not_applicable"
            rationale = "Installed product does not match the vulnerable product."
        else:
            try:
                version = MajorMinorVersion.parse(asset["version"])
            except ValueError:
                status = "unknown"
                rationale = "Installed version could not be compared deterministically."
            else:
                if affected_versions.is_affected(version):
                    status = "affected"
                    rationale = (
                        f"Installed version {asset['version']} is below "
                        f"{vulnerability['affected_before']}."
                    )
                else:
                    status = "not_affected"
                    rationale = (
                        f"Installed version {asset['version']} is not below "
                        f"{vulnerability['affected_before']}."
                    )

        assessments.append(
            AssetAssessment(
                asset_id=asset["asset_id"],
                status=status,
                rationale=rationale,
            )
        )

    return tuple(assessments)
