"""Diagnose LlamaIndex gateway attempts for the canonical product-mismatch scenario."""

import asyncio
import json
from dataclasses import asdict, dataclass

from agentic_lab.adapters.fixtures.evaluation import load_evaluation_scenarios
from agentic_lab.adapters.gateway import gateway_model_alias
from agentic_lab.adapters.llamaindex.workflow import LlamaIndexWorkflowRuntime
from agentic_lab.application.evaluation import EvaluationScenario
from agentic_lab.application.evidence import AnalysisEvidenceBundle
from agentic_lab.application.validated_analysis import ValidatedAnalysisOutput

_SCENARIO_ID = "product-mismatch"


@dataclass(frozen=True, slots=True)
class AttemptAssetStatus:
    """Capture only the asset identity and applicability status from one LLM attempt."""

    asset_id: str
    status: str


@dataclass(frozen=True, slots=True)
class AttemptDiagnostic:
    """Expose a minimal, secret-free view of one deterministic evaluator decision."""

    attempt: int
    input_feedback_present: bool
    validation_passed: bool
    validation_reason: str
    assets: tuple[AttemptAssetStatus, ...]


def load_product_mismatch_scenario() -> EvaluationScenario:
    """Return the single canonical product-mismatch scenario or fail closed."""
    matches = tuple(
        scenario
        for scenario in load_evaluation_scenarios()
        if scenario.scenario_id == _SCENARIO_ID
    )
    if len(matches) != 1:
        raise RuntimeError(f"Expected exactly one {_SCENARIO_ID!r} evaluation scenario")
    return matches[0]


def build_evidence_bundle(scenario: EvaluationScenario) -> AnalysisEvidenceBundle:
    """Convert the canonical scenario into the normal application evidence contract."""
    return {
        "vulnerability": scenario.vulnerability,
        "assets": scenario.assets,
        "policy": scenario.policy,
    }


def build_attempt_diagnostics(
    output: ValidatedAnalysisOutput,
) -> tuple[AttemptDiagnostic, ...]:
    """Return evaluator trace data without prompts, rationales, or feedback text."""
    return tuple(
        AttemptDiagnostic(
            attempt=evidence.attempt,
            input_feedback_present=evidence.input_feedback is not None,
            validation_passed=evidence.validation_passed,
            validation_reason=evidence.validation_reason,
            assets=tuple(
                AttemptAssetStatus(
                    asset_id=assessment.asset_id,
                    status=assessment.status,
                )
                for assessment in evidence.draft.assets
            ),
        )
        for evidence in output.attempt_trace
    )


async def diagnose() -> None:
    """Execute only product-mismatch and print a sanitized per-attempt trace."""
    scenario = load_product_mismatch_scenario()
    runtime = LlamaIndexWorkflowRuntime(gateway_model_alias())
    execution = await runtime.arun(evidence_bundle=build_evidence_bundle(scenario))
    diagnostics = build_attempt_diagnostics(execution.output)

    for diagnostic in diagnostics:
        print(
            json.dumps(
                {
                    "type": "llamaindex_gateway_attempt_diagnostic",
                    "scenario_id": scenario.scenario_id,
                    **asdict(diagnostic),
                }
            )
        )

    expected = [
        {"asset_id": item.asset_id, "status": item.status}
        for item in scenario.expected_assets
    ]
    usage = execution.usage
    output = execution.output
    print(
        json.dumps(
            {
                "type": "llamaindex_gateway_diagnostic_summary",
                "scenario_id": scenario.scenario_id,
                "model_alias": gateway_model_alias(),
                "expected_assets": expected,
                "analysis_source": output.analysis_source,
                "validation_passed": output.validation_passed,
                "analysis_attempts": output.analysis_attempts,
                "model_calls": usage.model_calls,
                "input_tokens": usage.input_tokens,
                "output_tokens": usage.output_tokens,
                "total_tokens": usage.total_tokens,
            }
        )
    )


def main() -> None:
    """Run the focused provider-backed diagnostic without writing artifacts."""
    asyncio.run(diagnose())


if __name__ == "__main__":
    main()
