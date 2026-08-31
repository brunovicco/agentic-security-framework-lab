"""Deterministic LangGraph vulnerability-analysis workflow."""

# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false

from typing import cast

from langgraph.graph import END, START, StateGraph

from agentic_lab.adapters.langchain.tools import (
    get_asset_inventory,
    get_security_policy,
    get_vulnerability_evidence,
)
from agentic_lab.adapters.langgraph.state import (
    AnalysisGraphInput,
    AnalysisGraphOutput,
    AnalysisGraphState,
)
from agentic_lab.application.contracts import (
    AnalysisResult,
    ApplicabilityStatus,
    AssetAssessment,
    Severity,
)
from agentic_lab.application.evidence import (
    AssetInventoryItem,
    SecurityPolicy,
    VulnerabilityEvidence,
)
from agentic_lab.application.validated_analysis import evaluate_human_review_policy
from agentic_lab.domain.versioning import MajorMinorVersion
from agentic_lab.domain.vulnerability import AffectedBeforeVersionRule


def collect_evidence(state: AnalysisGraphInput) -> AnalysisGraphState:
    """Collect deterministic evidence through LangChain tools."""
    vulnerability = cast(
        VulnerabilityEvidence,
        get_vulnerability_evidence.invoke(
            {"cve_id": state["cve_id"]},
        ),
    )
    assets = cast(
        tuple[AssetInventoryItem, ...],
        get_asset_inventory.invoke({}),
    )
    policy = cast(
        SecurityPolicy,
        get_security_policy.invoke({}),
    )

    return {
        "cve_id": state["cve_id"],
        "vulnerability": vulnerability,
        "assets": assets,
        "policy": policy,
    }


def analyze_installations(state: AnalysisGraphState) -> AnalysisGraphState:
    """Deterministically assess inventory against affected versions."""
    vulnerability = state.get("vulnerability")
    assets = state.get("assets")

    if vulnerability is None or assets is None:
        raise RuntimeError("Installation analysis requires vulnerability and asset evidence")

    affected_versions = AffectedBeforeVersionRule(
        upper_bound_exclusive=MajorMinorVersion.parse(
            vulnerability["affected_before"],
        ),
    )

    assessments: list[AssetAssessment] = []

    for asset in assets:
        status: ApplicabilityStatus

        if asset["product"] != vulnerability["product"]:
            status = "not_applicable"
            rationale = "Installed product does not match the vulnerable product."
        else:
            try:
                installed_version = MajorMinorVersion.parse(asset["version"])
            except ValueError:
                status = "unknown"
                rationale = "Installed version could not be compared deterministically."
            else:
                if affected_versions.is_affected(installed_version):
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

    return {
        "assessments": tuple(assessments),
    }


def apply_policy(state: AnalysisGraphState) -> AnalysisGraphState:
    """Apply deterministic human-review policy to the analysis."""
    vulnerability = state.get("vulnerability")
    policy = state.get("policy")
    assessments = state.get("assessments")
    assets = state.get("assets")

    if vulnerability is None or policy is None or assessments is None or assets is None:
        raise RuntimeError(
            "Policy evaluation requires vulnerability, inventory, policy, and assessment state"
        )

    return {
        "requires_human_review": evaluate_human_review_policy(
            vulnerability=vulnerability,
            assets=assets,
            policy=policy,
            assessments=assessments,
        )
    }


def finalize(state: AnalysisGraphState) -> AnalysisGraphState:
    """Build the shared framework-independent analysis result."""
    cve_id = state.get("cve_id")
    vulnerability = state.get("vulnerability")
    assessments = state.get("assessments")
    requires_human_review = state.get("requires_human_review")

    if (
        cve_id is None
        or vulnerability is None
        or assessments is None
        or requires_human_review is None
    ):
        raise RuntimeError(
            "Finalization requires CVE, vulnerability, assessment, and policy-decision state"
        )

    has_affected_asset = any(assessment.status == "affected" for assessment in assessments)

    recommendation = (
        "Prioritize remediation for affected assets."
        if has_affected_asset
        else "No affected assets were identified."
    )

    result = AnalysisResult(
        cve_id=cve_id,
        severity=cast(Severity, vulnerability["severity"]),
        assets=assessments,
        recommendation=recommendation,
        confidence=1.0,
        evidence=(
            "fixture:vulnerability",
            "fixture:asset-inventory",
            "fixture:security-policy",
        ),
        requires_human_review=requires_human_review,
    )

    return {
        "result": result,
    }


_builder = StateGraph(
    AnalysisGraphState,
    input_schema=AnalysisGraphInput,
    output_schema=AnalysisGraphOutput,
)

_builder.add_node("collect_evidence", collect_evidence)
_builder.add_node("analyze_installations", analyze_installations)
_builder.add_node("apply_policy", apply_policy)
_builder.add_node("finalize", finalize)

_builder.add_edge(START, "collect_evidence")
_builder.add_edge("collect_evidence", "analyze_installations")
_builder.add_edge("analyze_installations", "apply_policy")
_builder.add_edge("apply_policy", "finalize")
_builder.add_edge("finalize", END)

_analysis_graph = _builder.compile()


def run_analysis_graph(cve_id: str) -> AnalysisGraphOutput:
    """Run the compiled vulnerability-analysis graph."""
    return cast(
        AnalysisGraphOutput,
        _analysis_graph.invoke(
            {
                "cve_id": cve_id,
            }
        ),
    )
