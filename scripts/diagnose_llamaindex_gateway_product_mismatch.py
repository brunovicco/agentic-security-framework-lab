"""Diagnose LlamaIndex gateway product-mismatch behavior with controlled sequencing."""

import argparse
import asyncio
import json
from dataclasses import asdict, dataclass
from typing import Literal, cast

from agentic_lab.adapters.fixtures.evaluation import load_evaluation_scenarios
from agentic_lab.adapters.gateway import gateway_model_alias
from agentic_lab.adapters.llamaindex.workflow import (
    LlamaIndexWorkflowExecution,
    LlamaIndexWorkflowRuntime,
)
from agentic_lab.application.evaluation import EvaluationScenario
from agentic_lab.application.evidence import AnalysisEvidenceBundle
from agentic_lab.application.validated_analysis import ValidatedAnalysisOutput

_TARGET_SCENARIO_ID = "product-mismatch"
_PRELUDE_SCENARIO_ID = "baseline-mixed"
_DEFAULT_RUNS = 3
DiagnosticMode = Literal["isolated", "after_baseline"]


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


@dataclass(frozen=True, slots=True)
class DiagnosticSampleSummary:
    """Summarize one target execution without persisting model-generated text."""

    mode: DiagnosticMode
    sample: int
    analysis_source: str
    validation_passed: bool
    first_attempt_validation_passed: bool
    analysis_attempts: int
    model_calls: int
    input_tokens: int
    output_tokens: int
    total_tokens: int


def parse_runs() -> int:
    """Return the number of samples per diagnostic mode."""
    parser = argparse.ArgumentParser(
        description=(
            "Compare isolated product-mismatch executions with executions that follow "
            "the canonical baseline scenario."
        )
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=_DEFAULT_RUNS,
        help="Number of product-mismatch samples per diagnostic mode.",
    )
    args = parser.parse_args()
    runs = cast(int, args.runs)
    if runs < 1:
        raise ValueError("--runs must be at least 1")
    return runs


def load_scenario(scenario_id: str) -> EvaluationScenario:
    """Return one canonical scenario by id or fail closed."""
    matches = tuple(
        scenario
        for scenario in load_evaluation_scenarios()
        if scenario.scenario_id == scenario_id
    )
    if len(matches) != 1:
        raise RuntimeError(f"Expected exactly one {scenario_id!r} evaluation scenario")
    return matches[0]


def load_product_mismatch_scenario() -> EvaluationScenario:
    """Return the canonical product-mismatch scenario."""
    return load_scenario(_TARGET_SCENARIO_ID)


def load_baseline_scenario() -> EvaluationScenario:
    """Return the canonical baseline scenario used as the sequence prelude."""
    return load_scenario(_PRELUDE_SCENARIO_ID)


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


def summarize_execution(
    mode: DiagnosticMode,
    sample: int,
    execution: LlamaIndexWorkflowExecution,
) -> DiagnosticSampleSummary:
    """Build a status-level summary for one target execution."""
    output = execution.output
    usage = execution.usage
    first_attempt_passed = bool(
        output.attempt_trace and output.attempt_trace[0].validation_passed
    )
    return DiagnosticSampleSummary(
        mode=mode,
        sample=sample,
        analysis_source=output.analysis_source,
        validation_passed=output.validation_passed,
        first_attempt_validation_passed=first_attempt_passed,
        analysis_attempts=output.analysis_attempts,
        model_calls=usage.model_calls,
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        total_tokens=usage.total_tokens,
    )


def emit_target_diagnostics(
    scenario: EvaluationScenario,
    summary: DiagnosticSampleSummary,
    output: ValidatedAnalysisOutput,
) -> None:
    """Print sanitized attempt-level and sample-level diagnostics."""
    for diagnostic in build_attempt_diagnostics(output):
        print(
            json.dumps(
                {
                    "type": "llamaindex_gateway_attempt_diagnostic",
                    "scenario_id": scenario.scenario_id,
                    "mode": summary.mode,
                    "sample": summary.sample,
                    **asdict(diagnostic),
                }
            )
        )

    print(
        json.dumps(
            {
                "type": "llamaindex_gateway_diagnostic_summary",
                "scenario_id": scenario.scenario_id,
                "model_alias": gateway_model_alias(),
                **asdict(summary),
            }
        )
    )


async def run_target_sample(
    runtime: LlamaIndexWorkflowRuntime,
    scenario: EvaluationScenario,
    *,
    mode: DiagnosticMode,
    sample: int,
) -> DiagnosticSampleSummary:
    """Execute one product-mismatch sample and print its sanitized trace."""
    execution = await runtime.arun(evidence_bundle=build_evidence_bundle(scenario))
    summary = summarize_execution(mode, sample, execution)
    emit_target_diagnostics(scenario, summary, execution.output)
    return summary


async def run_prelude(
    runtime: LlamaIndexWorkflowRuntime,
    scenario: EvaluationScenario,
    *,
    sample: int,
) -> None:
    """Execute the baseline prelude and report only validation/usage metadata."""
    execution = await runtime.arun(evidence_bundle=build_evidence_bundle(scenario))
    output = execution.output
    usage = execution.usage
    print(
        json.dumps(
            {
                "type": "llamaindex_gateway_diagnostic_prelude",
                "scenario_id": scenario.scenario_id,
                "sample": sample,
                "analysis_source": output.analysis_source,
                "validation_passed": output.validation_passed,
                "analysis_attempts": output.analysis_attempts,
                "model_calls": usage.model_calls,
                "total_tokens": usage.total_tokens,
            }
        )
    )


async def diagnose(repetitions: int) -> None:
    """Compare isolated and baseline-preceded product-mismatch executions."""
    if repetitions < 1:
        raise ValueError("repetitions must be at least 1")

    target = load_product_mismatch_scenario()
    baseline = load_baseline_scenario()
    summaries: list[DiagnosticSampleSummary] = []

    for sample in range(1, repetitions + 1):
        runtime = LlamaIndexWorkflowRuntime(gateway_model_alias())
        summaries.append(
            await run_target_sample(
                runtime,
                target,
                mode="isolated",
                sample=sample,
            )
        )

    for sample in range(1, repetitions + 1):
        runtime = LlamaIndexWorkflowRuntime(gateway_model_alias())
        await run_prelude(runtime, baseline, sample=sample)
        summaries.append(
            await run_target_sample(
                runtime,
                target,
                mode="after_baseline",
                sample=sample,
            )
        )

    for mode in ("isolated", "after_baseline"):
        mode_summaries = [summary for summary in summaries if summary.mode == mode]
        print(
            json.dumps(
                {
                    "type": "llamaindex_gateway_diagnostic_matrix_summary",
                    "mode": mode,
                    "samples": len(mode_summaries),
                    "first_attempt_accepts": sum(
                        summary.first_attempt_validation_passed
                        for summary in mode_summaries
                    ),
                    "llm_final_accepts": sum(
                        summary.analysis_source == "llm" and summary.validation_passed
                        for summary in mode_summaries
                    ),
                    "fallbacks": sum(
                        summary.analysis_source == "oracle_fallback"
                        for summary in mode_summaries
                    ),
                }
            )
        )


def main() -> None:
    """Run the provider-backed diagnostic matrix without writing artifacts."""
    asyncio.run(diagnose(parse_runs()))


if __name__ == "__main__":
    main()
