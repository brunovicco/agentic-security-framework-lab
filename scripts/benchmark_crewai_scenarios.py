"""Benchmark CrewAI across the shared vulnerability evaluation dataset."""

import argparse
import json
import math
import os
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean, median
from time import perf_counter
from typing import Literal, cast

from agentic_lab.adapters.crewai.analyzer import (
    CrewAIRuntime,
    CrewAIVulnerabilityAnalyzer,
)
from agentic_lab.adapters.fixtures.evaluation import load_evaluation_scenarios
from agentic_lab.application.contracts import AssetAssessment
from agentic_lab.application.evaluation import EvaluationScenario
from agentic_lab.application.evidence import AnalysisEvidenceBundle
from agentic_lab.application.validated_analysis import run_validated_analysis

_MODEL_ENV = "AGENTIC_LAB_MODEL"
_FRAMEWORK = "crewai"
_PATTERN = "single_agent_external_evaluator_optimizer"


@dataclass(frozen=True, slots=True)
class ScenarioRun:
    """Capture one CrewAI execution against one evaluation scenario."""

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
    """Summarize repeated CrewAI executions of one evaluation scenario."""

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
    """Summarize the complete CrewAI multi-scenario benchmark."""

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
        description="Benchmark CrewAI across the shared evaluation dataset.",
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
    """Return the model configured for the benchmark."""
    model_name = os.environ.get(_MODEL_ENV)

    if not model_name:
        raise RuntimeError(f"{_MODEL_ENV} must identify the benchmark model")

    return model_name


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
    """Aggregate metrics across every CrewAI scenario and execution."""
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
    """Render a human-readable CrewAI benchmark report."""
    lines = [
        "# CrewAI Agentic Security Benchmark",
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
        (f"- First-attempt acceptance: **{overall.first_attempt_acceptance_rate:.1%}**"),
        f"- Retry rate: **{overall.retry_rate:.1%}**",
        (f"- Recovery rate: **{format_recovery_rate(overall.retry_rate, overall.recovery_rate)}**"),
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
            "| Scenario | Accuracy | First pass | Retry | Recovery | "
            "Fallback | Model calls | p50 ms | p95 ms | Mean tokens |"
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
                "`expected_accuracy` compares the final system result with the "
                "framework-neutral evaluation dataset."
            ),
            "",
            (
                "The CrewAI baseline uses one structured Agent + Task + Crew for "
                "probabilistic reasoning. Deterministic evaluation, bounded retry, "
                "fallback, and human-review policy remain application-owned."
            ),
            "",
            (
                "`analysis_attempts` counts application-level evaluator cycles. "
                "`model_calls` comes from CrewAI `successful_requests`, so it may "
                "exceed the number of analysis attempts if CrewAI performs extra "
                "provider requests internally."
            ),
            "",
            (
                "The adversarial scenario tests whether instruction-like text "
                "embedded in untrusted asset data influences classification. It is "
                "a focused security test, not proof of general prompt-injection resistance."
            ),
            "",
            (
                "Latency percentiles are descriptive for this benchmark sample size "
                "and should not be interpreted as production SLO measurements."
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
    """Persist machine-readable and human-readable CrewAI artifacts."""
    generated_at = datetime.now(UTC).isoformat()
    output_dir = Path("artifacts/benchmarks/crewai")
    output_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "schema_version": "1",
        "generated_at_utc": generated_at,
        "framework": _FRAMEWORK,
        "pattern": _PATTERN,
        "model": model_name,
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


def main() -> None:
    """Execute every scenario and print per-run and aggregate CrewAI results."""
    repetitions = parse_runs()
    model_name = require_model_name()
    scenarios = load_evaluation_scenarios()
    runtime = CrewAIRuntime(model_name)
    analyzer = CrewAIVulnerabilityAnalyzer(runtime)
    all_runs: list[ScenarioRun] = []
    scenario_summaries: list[ScenarioSummary] = []

    for scenario in scenarios:
        evidence_bundle = build_evidence_bundle(scenario)
        scenario_runs: list[ScenarioRun] = []

        for iteration in range(1, repetitions + 1):
            stale_usage = runtime.consume_usage()
            if stale_usage.total_tokens or stale_usage.model_calls:
                raise RuntimeError("CrewAI usage telemetry was not clean before benchmark run")

            started_at = perf_counter()
            output = run_validated_analysis(
                analyzer=analyzer,
                evidence_bundle=evidence_bundle,
            )
            latency_ms = (perf_counter() - started_at) * 1000
            usage = runtime.consume_usage()

            if usage.model_calls < output.analysis_attempts or usage.total_tokens <= 0:
                raise RuntimeError(
                    "CrewAI did not expose complete token/request telemetry for benchmark execution"
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
                expected_match=matches_expected(
                    scenario,
                    output.result.assets,
                ),
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


if __name__ == "__main__":
    main()
