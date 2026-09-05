"""Benchmark LlamaIndex Workflow across the shared vulnerability evaluation dataset."""

import argparse
import asyncio
import json
import math
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean, median
from time import perf_counter
from typing import Literal, cast

from agentic_lab.adapters.fixtures.evaluation import load_evaluation_scenarios
from agentic_lab.adapters.gateway import gateway_model_alias
from agentic_lab.adapters.llamaindex.workflow import LlamaIndexWorkflowRuntime
from agentic_lab.application.contracts import AssetAssessment
from agentic_lab.application.evaluation import EvaluationScenario
from agentic_lab.application.evidence import AnalysisEvidenceBundle

_FRAMEWORK = "llamaindex"
_PATTERN = "workflow_structured_predict_evaluator_optimizer"


@dataclass(frozen=True, slots=True)
class ScenarioRun:
    """Capture one LlamaIndex Workflow execution against one evaluation scenario."""

    scenario_id: str
    iteration: int
    tags: tuple[str, ...]
    model: str
    latency_ms: float
    analysis_source: Literal["llm", "oracle_fallback"]
    validation_passed: bool
    analysis_attempts: int
    model_calls: int
    expected_match: bool
    confidence: float
    input_tokens: int
    output_tokens: int
    total_tokens: int


@dataclass(frozen=True, slots=True)
class ScenarioSummary:
    """Summarize repeated LlamaIndex Workflow executions of one scenario."""

    scenario_id: str
    tags: tuple[str, ...]
    runs: int
    expected_passes: int
    expected_accuracy: float
    first_attempt_acceptance_rate: float
    retry_rate: float
    recovery_rate: float
    fallback_rate: float
    mean_model_calls: float
    mean_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    mean_confidence: float
    mean_total_tokens: float


@dataclass(frozen=True, slots=True)
class OverallSummary:
    """Summarize the complete LlamaIndex Workflow benchmark."""

    framework: str
    pattern: str
    model: str
    scenarios: int
    total_runs: int
    expected_passes: int
    expected_accuracy: float
    first_attempt_acceptance_rate: float
    retry_rate: float
    recovery_rate: float
    fallback_rate: float
    mean_model_calls: float
    total_model_calls: int
    mean_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    mean_total_tokens: float
    total_tokens: int


def parse_runs() -> int:
    """Parse and validate repetitions per evaluation scenario."""
    parser = argparse.ArgumentParser(
        description="Benchmark LlamaIndex Workflow across the shared evaluation dataset.",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=1,
        help="Number of executions per evaluation scenario.",
    )
    args = parser.parse_args()
    runs = cast(int, args.runs)
    if runs < 1:
        raise ValueError("--runs must be at least 1")
    return runs


def require_model_name() -> str:
    """Return the governed gateway alias used by the benchmark runtime."""
    return gateway_model_alias()


def nearest_rank_percentile(values: list[float], percentile: float) -> float:
    """Calculate a percentile using nearest-rank semantics."""
    if not values:
        raise ValueError("Percentile requires at least one value")
    if not 0 < percentile <= 1:
        raise ValueError("Percentile must be greater than 0 and at most 1")
    ordered = sorted(values)
    rank = math.ceil(percentile * len(ordered))
    return ordered[rank - 1]


def build_evidence_bundle(scenario: EvaluationScenario) -> AnalysisEvidenceBundle:
    """Convert an evaluation scenario into executable evidence."""
    return {
        "vulnerability": scenario.vulnerability,
        "assets": scenario.assets,
        "policy": scenario.policy,
    }


def matches_expected(
    scenario: EvaluationScenario,
    observed_assets: tuple[AssetAssessment, ...],
) -> bool:
    """Compare final asset statuses with external evaluation truth."""
    expected = {assessment.asset_id: assessment.status for assessment in scenario.expected_assets}
    observed = {assessment.asset_id: assessment.status for assessment in observed_assets}
    return observed == expected and len(observed_assets) == len(scenario.expected_assets)


def summarize_scenario(
    scenario: EvaluationScenario,
    runs: list[ScenarioRun],
) -> ScenarioSummary:
    """Aggregate benchmark metrics for one scenario."""
    if not runs:
        raise ValueError("Scenario summary requires at least one run")

    total = len(runs)
    expected_passes = sum(run.expected_match for run in runs)
    first_attempt_accepts = sum(
        run.analysis_source == "llm" and run.analysis_attempts == 1 for run in runs
    )
    retried = sum(run.analysis_attempts > 1 for run in runs)
    recovered = sum(run.analysis_attempts > 1 and run.analysis_source == "llm" for run in runs)
    fallbacks = sum(run.analysis_source == "oracle_fallback" for run in runs)
    latencies = [run.latency_ms for run in runs]
    recovery_rate = recovered / retried if retried else 0.0

    return ScenarioSummary(
        scenario_id=scenario.scenario_id,
        tags=scenario.tags,
        runs=total,
        expected_passes=expected_passes,
        expected_accuracy=expected_passes / total,
        first_attempt_acceptance_rate=first_attempt_accepts / total,
        retry_rate=retried / total,
        recovery_rate=recovery_rate,
        fallback_rate=fallbacks / total,
        mean_model_calls=round(mean(run.model_calls for run in runs), 2),
        mean_latency_ms=round(mean(latencies), 2),
        p50_latency_ms=round(median(latencies), 2),
        p95_latency_ms=round(nearest_rank_percentile(latencies, 0.95), 2),
        mean_confidence=round(mean(run.confidence for run in runs), 4),
        mean_total_tokens=round(mean(run.total_tokens for run in runs), 2),
    )


def summarize_overall(
    model_name: str,
    scenario_count: int,
    runs: list[ScenarioRun],
) -> OverallSummary:
    """Aggregate metrics across every LlamaIndex Workflow scenario and execution."""
    if not runs:
        raise ValueError("Overall summary requires at least one run")

    total = len(runs)
    expected_passes = sum(run.expected_match for run in runs)
    first_attempt_accepts = sum(
        run.analysis_source == "llm" and run.analysis_attempts == 1 for run in runs
    )
    retried = sum(run.analysis_attempts > 1 for run in runs)
    recovered = sum(run.analysis_attempts > 1 and run.analysis_source == "llm" for run in runs)
    fallbacks = sum(run.analysis_source == "oracle_fallback" for run in runs)
    latencies = [run.latency_ms for run in runs]
    recovery_rate = recovered / retried if retried else 0.0

    return OverallSummary(
        framework=_FRAMEWORK,
        pattern=_PATTERN,
        model=model_name,
        scenarios=scenario_count,
        total_runs=total,
        expected_passes=expected_passes,
        expected_accuracy=expected_passes / total,
        first_attempt_acceptance_rate=first_attempt_accepts / total,
        retry_rate=retried / total,
        recovery_rate=recovery_rate,
        fallback_rate=fallbacks / total,
        mean_model_calls=round(mean(run.model_calls for run in runs), 2),
        total_model_calls=sum(run.model_calls for run in runs),
        mean_latency_ms=round(mean(latencies), 2),
        p50_latency_ms=round(median(latencies), 2),
        p95_latency_ms=round(nearest_rank_percentile(latencies, 0.95), 2),
        mean_total_tokens=round(mean(run.total_tokens for run in runs), 2),
        total_tokens=sum(run.total_tokens for run in runs),
    )


def format_recovery_rate(retry_rate: float, recovery_rate: float) -> str:
    """Format recovery only when retry behavior was exercised."""
    if retry_rate == 0:
        return "N/A"
    return f"{recovery_rate:.1%}"


def render_markdown_report(
    generated_at_utc: str,
    model_name: str,
    scenario_summaries: list[ScenarioSummary],
    overall: OverallSummary,
) -> str:
    """Render a human-readable LlamaIndex Workflow benchmark report."""
    lines = [
        "# LlamaIndex Workflow Agentic Security Benchmark",
        "",
        f"Generated: `{generated_at_utc}`",
        "",
        f"Model: `{model_name}`",
        "",
        f"Framework: `{_FRAMEWORK}`",
        "",
        f"Pattern: `{_PATTERN}`",
        "",
        "## Overall results",
        "",
        f"- Scenarios: **{overall.scenarios}**",
        f"- Total runs: **{overall.total_runs}**",
        f"- Expected accuracy: **{overall.expected_accuracy:.1%}**",
        f"- First-attempt acceptance: **{overall.first_attempt_acceptance_rate:.1%}**",
        f"- Retry rate: **{overall.retry_rate:.1%}**",
        f"- Recovery rate: **{format_recovery_rate(overall.retry_rate, overall.recovery_rate)}**",
        f"- Fallback rate: **{overall.fallback_rate:.1%}**",
        f"- Mean model calls: **{overall.mean_model_calls:.2f}**",
        f"- Mean latency: **{overall.mean_latency_ms:.2f} ms**",
        f"- p50 latency: **{overall.p50_latency_ms:.2f} ms**",
        f"- p95 latency: **{overall.p95_latency_ms:.2f} ms**",
        f"- Mean tokens: **{overall.mean_total_tokens:.2f}**",
        f"- Total tokens: **{overall.total_tokens}**",
        "",
        "## Scenario results",
        "",
        (
            "| Scenario | Accuracy | First pass | Retry | Recovery | Fallback | "
            "Model calls | p50 ms | p95 ms | Mean tokens |"
        ),
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]

    for summary in scenario_summaries:
        lines.append(
            "| "
            f"{summary.scenario_id} | "
            f"{summary.expected_accuracy:.1%} | "
            f"{summary.first_attempt_acceptance_rate:.1%} | "
            f"{summary.retry_rate:.1%} | "
            f"{format_recovery_rate(summary.retry_rate, summary.recovery_rate)} | "
            f"{summary.fallback_rate:.1%} | "
            f"{summary.mean_model_calls:.2f} | "
            f"{summary.p50_latency_ms:.2f} | "
            f"{summary.p95_latency_ms:.2f} | "
            f"{summary.mean_total_tokens:.2f} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            (
                "This variant uses native LlamaIndex Workflows for event-driven "
                "orchestration and LlamaIndex `structured_predict()` for probabilistic "
                "reasoning."
            ),
            "",
            (
                "Deterministic applicability validation, evaluator feedback, bounded "
                "retry, oracle fallback, and human-review policy use the same shared "
                "application controls as the other framework variants."
            ),
            "",
            (
                "Each Workflow execution creates an isolated LlamaIndex runtime and "
                "uses `TokenCountingHandler` to report prompt, completion, total tokens, "
                "and observed LLM callback events for that execution."
            ),
            "",
            (
                "The benchmark drives the async-first Workflow through one process-level "
                "event loop and measures each native `arun()` execution independently."
            ),
            "",
            (
                "Sampling uses the provider-supported GPT-5 default configured by the "
                "adapter (`temperature=1.0`) and must not be described as deterministic."
            ),
            "",
            (
                "The adversarial scenario is a focused instruction/data-boundary "
                "test and must not be interpreted as general prompt-injection resistance."
            ),
            "",
            (
                "Latency percentiles are descriptive for this small benchmark sample "
                "and should not be interpreted as production SLO evidence."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def write_benchmark_artifacts(
    model_name: str,
    repetitions: int,
    runs: list[ScenarioRun],
    scenario_summaries: list[ScenarioSummary],
    overall: OverallSummary,
) -> None:
    """Persist machine-readable and human-readable LlamaIndex Workflow artifacts."""
    generated_at = datetime.now(UTC).isoformat()
    output_dir = Path("artifacts/benchmarks/llamaindex-workflow")
    output_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "schema_version": "1",
        "generated_at_utc": generated_at,
        "framework": _FRAMEWORK,
        "pattern": _PATTERN,
        "model": model_name,
        "sampling": "provider_default",
        "repetitions_per_scenario": repetitions,
        "runs": [asdict(run) for run in runs],
        "scenario_summaries": [asdict(summary) for summary in scenario_summaries],
        "overall_summary": asdict(overall),
    }

    json_path = output_dir / "latest.json"
    markdown_path = output_dir / "latest.md"
    json_path.write_text(json.dumps(payload, indent=2) + "\n")
    markdown_path.write_text(
        render_markdown_report(
            generated_at_utc=generated_at,
            model_name=model_name,
            scenario_summaries=scenario_summaries,
            overall=overall,
        )
    )

    print()
    print(f"artifact_json: {json_path}")
    print(f"artifact_markdown: {markdown_path}")


async def run_benchmark(repetitions: int, model_name: str) -> None:
    """Execute every scenario through the native async LlamaIndex Workflow path."""
    scenarios = load_evaluation_scenarios()
    runtime = LlamaIndexWorkflowRuntime(model_name)
    all_runs: list[ScenarioRun] = []
    scenario_summaries: list[ScenarioSummary] = []

    for scenario in scenarios:
        evidence_bundle = build_evidence_bundle(scenario)
        scenario_runs: list[ScenarioRun] = []

        for iteration in range(1, repetitions + 1):
            started_at = perf_counter()
            execution = await runtime.arun(evidence_bundle=evidence_bundle)
            latency_ms = (perf_counter() - started_at) * 1000
            output = execution.output
            usage = execution.usage

            if (
                usage.model_calls < output.analysis_attempts
                or usage.input_tokens <= 0
                or usage.output_tokens <= 0
                or usage.total_tokens <= 0
            ):
                raise RuntimeError(
                    "LlamaIndex Workflow did not expose complete token/request telemetry "
                    "for the run"
                )

            run = ScenarioRun(
                scenario_id=scenario.scenario_id,
                iteration=iteration,
                tags=scenario.tags,
                model=model_name,
                latency_ms=round(latency_ms, 2),
                analysis_source=output.analysis_source,
                validation_passed=output.validation_passed,
                analysis_attempts=output.analysis_attempts,
                model_calls=usage.model_calls,
                expected_match=matches_expected(scenario, output.result.assets),
                confidence=output.result.confidence,
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                total_tokens=usage.total_tokens,
            )
            scenario_runs.append(run)
            all_runs.append(run)
            print(json.dumps({"type": "run", **asdict(run)}))

        summary = summarize_scenario(scenario, scenario_runs)
        scenario_summaries.append(summary)
        print(json.dumps({"type": "scenario_summary", **asdict(summary)}))

    overall = summarize_overall(
        model_name=model_name,
        scenario_count=len(scenarios),
        runs=all_runs,
    )
    print()
    print("overall_summary")
    print(json.dumps(asdict(overall), indent=2))
    write_benchmark_artifacts(
        model_name=model_name,
        repetitions=repetitions,
        runs=all_runs,
        scenario_summaries=scenario_summaries,
        overall=overall,
    )


def main() -> None:
    """Parse configuration and execute the async-first Workflow benchmark."""
    repetitions = parse_runs()
    model_name = require_model_name()
    asyncio.run(run_benchmark(repetitions=repetitions, model_name=model_name))


if __name__ == "__main__":
    main()
