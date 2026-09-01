"""Run LangGraph against the dedicated adversarial security dataset."""

import argparse
import json
import math
import os
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean, median
from time import perf_counter
from typing import cast

from langchain_core.callbacks import get_usage_metadata_callback
from langchain_core.messages import UsageMetadata

from agentic_lab.adapters.fixtures.adversarial_evaluation import (
    load_adversarial_evaluation_scenarios,
)
from agentic_lab.adapters.langchain.analyzer import LangChainVulnerabilityAnalyzer
from agentic_lab.adapters.langchain.model import create_chat_model
from agentic_lab.adapters.langgraph.llm_graph import run_llm_analysis_graph_with_evidence
from agentic_lab.adapters.langgraph.state import LLMAnalysisGraphOutput
from agentic_lab.application.adversarial_evaluation import (
    AdversarialEvaluationScenario,
    AdversarialTrajectoryEvaluation,
    evaluate_adversarial_trajectory,
)
from agentic_lab.application.evidence import AnalysisEvidenceBundle
from agentic_lab.application.validated_analysis import (
    AnalysisSource,
    ValidatedAnalysisOutput,
)

_MODEL_ENV = "AGENTIC_LAB_MODEL"
_FRAMEWORK = "langgraph"
_PATTERN = "evaluator_optimizer_adversarial_attempt_evidence"
_SAMPLING = "provider_default"
_OUTPUT_DIR = Path("artifacts/adversarial/langgraph")


@dataclass(frozen=True, slots=True)
class TokenUsage:
    """Represent standardized token usage for one execution."""

    input_tokens: int
    output_tokens: int
    total_tokens: int


@dataclass(frozen=True, slots=True)
class AttemptTraceRecord:
    """Persist raw attempt evidence with deterministic attack classification."""

    attempt: int
    input_feedback: str | None
    draft_assets: tuple[tuple[str, str], ...]
    draft_recommendation: str
    draft_confidence: float
    validation_passed: bool
    validation_reason: str
    validation_feedback: str
    attack_succeeded: bool
    attack_signals: tuple[str, ...]
    deterministic_rejection: bool
    attack_survived_validation: bool


@dataclass(frozen=True, slots=True)
class AdversarialRun:
    """Capture one provider-backed adversarial execution."""

    scenario_id: str
    iteration: int
    attack_class: str
    tags: tuple[str, ...]
    model: str
    latency_ms: float
    analysis_source: AnalysisSource
    validation_passed: bool
    analysis_attempts: int
    model_calls: int
    task_match: bool
    security_passed: bool
    unsafe_acceptance: bool
    model_attack_success: bool
    deterministic_rejection_after_attack: bool
    recovery_after_rejection: bool
    fallback_containment: bool
    control_containment: bool
    asset_identity_integrity: bool
    human_review_integrity: bool
    recommendation_integrity: bool
    confidence_integrity: bool
    failed_security_assertions: tuple[str, ...]
    confidence: float
    input_tokens: int
    output_tokens: int
    total_tokens: int
    attempt_trace: tuple[AttemptTraceRecord, ...]


@dataclass(frozen=True, slots=True)
class AdversarialSummary:
    """Aggregate task, security, attack, control, and runtime metrics."""

    runs: int
    task_passes: int
    task_accuracy: float
    security_passes: int
    security_pass_rate: float
    model_attack_successes: int
    model_attack_success_rate: float
    deterministic_rejections_after_attack: int
    deterministic_rejection_after_attack_rate: float | None
    recoveries_after_rejection: int
    recovery_after_rejection_rate: float | None
    fallback_containments: int
    control_containments: int
    control_containment_rate: float | None
    unsafe_acceptances: int
    unsafe_acceptance_rate: float
    asset_identity_integrity_rate: float
    human_review_integrity_rate: float
    recommendation_integrity_rate: float
    confidence_integrity_rate: float
    retry_rate: float
    fallback_rate: float
    mean_model_calls: float
    mean_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    mean_total_tokens: float
    total_tokens: int


@dataclass(frozen=True, slots=True)
class ScenarioSummary:
    """Aggregate one adversarial scenario."""

    scenario_id: str
    attack_class: str
    tags: tuple[str, ...]
    metrics: AdversarialSummary


@dataclass(frozen=True, slots=True)
class OverallSummary:
    """Aggregate the complete LangGraph adversarial evaluation."""

    framework: str
    pattern: str
    model: str
    scenarios: int
    metrics: AdversarialSummary


def parse_runs() -> int:
    """Parse repetitions per adversarial scenario."""
    parser = argparse.ArgumentParser(
        description="Run LangGraph against the dedicated adversarial dataset.",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=1,
        help="Number of executions per adversarial scenario.",
    )
    args = parser.parse_args()
    runs = cast(int, args.runs)

    if runs < 1:
        raise ValueError("--runs must be at least 1")

    return runs


def require_model_name() -> str:
    """Return the configured provider model."""
    model_name = os.environ.get(_MODEL_ENV)

    if not model_name:
        raise RuntimeError(f"{_MODEL_ENV} must identify the benchmark model")

    return model_name


def aggregate_usage(usage_by_model: Mapping[str, UsageMetadata]) -> TokenUsage:
    """Aggregate standardized LangChain token usage."""
    return TokenUsage(
        input_tokens=sum(usage["input_tokens"] for usage in usage_by_model.values()),
        output_tokens=sum(usage["output_tokens"] for usage in usage_by_model.values()),
        total_tokens=sum(usage["total_tokens"] for usage in usage_by_model.values()),
    )


def nearest_rank_percentile(values: list[float], percentile: float) -> float:
    """Calculate a percentile using nearest-rank semantics."""
    if not values:
        raise ValueError("Percentile requires at least one value")

    if not 0 < percentile <= 1:
        raise ValueError("Percentile must be greater than 0 and at most 1")

    ordered = sorted(values)
    rank = math.ceil(percentile * len(ordered))
    return ordered[rank - 1]


def build_evidence_bundle(
    scenario: AdversarialEvaluationScenario,
) -> AnalysisEvidenceBundle:
    """Convert an adversarial scenario into executable evidence."""
    return {
        "vulnerability": scenario.vulnerability,
        "assets": scenario.assets,
        "policy": scenario.policy,
    }


def build_validated_output(output: LLMAnalysisGraphOutput) -> ValidatedAnalysisOutput:
    """Adapt LangGraph output to the framework-neutral adversarial evaluator."""
    return ValidatedAnalysisOutput(
        result=output["result"],
        analysis_source=output["analysis_source"],
        validation_passed=output["validation_passed"],
        validation_reason=output["validation_reason"],
        analysis_attempts=output["analysis_attempts"],
        attempt_trace=output["attempt_trace"],
    )


def build_attempt_trace(
    output: LLMAnalysisGraphOutput,
    trajectory: AdversarialTrajectoryEvaluation,
) -> tuple[AttemptTraceRecord, ...]:
    """Join raw attempt evidence to deterministic attack classifications."""
    raw_attempts = output["attempt_trace"]

    if len(raw_attempts) != len(trajectory.attempts):
        raise RuntimeError("Raw and classified attempt traces have different lengths")

    records: list[AttemptTraceRecord] = []

    for raw, classified in zip(raw_attempts, trajectory.attempts, strict=True):
        if raw.attempt != classified.attempt:
            raise RuntimeError("Raw and classified attempt numbers do not match")

        records.append(
            AttemptTraceRecord(
                attempt=raw.attempt,
                input_feedback=raw.input_feedback,
                draft_assets=tuple(
                    (assessment.asset_id, assessment.status)
                    for assessment in raw.draft.assets
                ),
                draft_recommendation=raw.draft.recommendation,
                draft_confidence=raw.draft.confidence,
                validation_passed=raw.validation_passed,
                validation_reason=raw.validation_reason,
                validation_feedback=raw.validation_feedback,
                attack_succeeded=classified.attack_succeeded,
                attack_signals=classified.attack_signals,
                deterministic_rejection=classified.deterministic_rejection,
                attack_survived_validation=classified.attack_survived_validation,
            )
        )

    return tuple(records)


def validate_run_telemetry(
    output: LLMAnalysisGraphOutput,
    usage: TokenUsage,
) -> None:
    """Fail closed when attempt or token telemetry is incomplete."""
    analysis_attempts = output["analysis_attempts"]
    trace = output["attempt_trace"]

    if analysis_attempts < 1:
        raise RuntimeError("Adversarial execution reported no analysis attempts")

    if len(trace) != analysis_attempts:
        raise RuntimeError("Attempt trace length does not match analysis_attempts")

    if usage.input_tokens <= 0 or usage.output_tokens <= 0 or usage.total_tokens <= 0:
        raise RuntimeError("Adversarial execution returned incomplete token telemetry")

    if usage.input_tokens + usage.output_tokens != usage.total_tokens:
        raise RuntimeError("Adversarial token telemetry does not add up")


def optional_rate(numerator: int, denominator: int) -> float | None:
    """Return a rate only when its conditional denominator was exercised."""
    if denominator == 0:
        return None

    return numerator / denominator


def summarize_runs(runs: list[AdversarialRun]) -> AdversarialSummary:
    """Aggregate adversarial metrics over one or more runs."""
    if not runs:
        raise ValueError("Adversarial summary requires at least one run")

    total = len(runs)
    task_passes = sum(run.task_match for run in runs)
    security_passes = sum(run.security_passed for run in runs)
    attack_successes = sum(run.model_attack_success for run in runs)
    attack_rejections = sum(run.deterministic_rejection_after_attack for run in runs)
    recoveries = sum(run.recovery_after_rejection for run in runs)
    fallback_containments = sum(run.fallback_containment for run in runs)
    control_containments = sum(run.control_containment for run in runs)
    unsafe_acceptances = sum(run.unsafe_acceptance for run in runs)
    retried = sum(run.analysis_attempts > 1 for run in runs)
    fallbacks = sum(run.analysis_source == "oracle_fallback" for run in runs)
    latencies = [run.latency_ms for run in runs]

    return AdversarialSummary(
        runs=total,
        task_passes=task_passes,
        task_accuracy=task_passes / total,
        security_passes=security_passes,
        security_pass_rate=security_passes / total,
        model_attack_successes=attack_successes,
        model_attack_success_rate=attack_successes / total,
        deterministic_rejections_after_attack=attack_rejections,
        deterministic_rejection_after_attack_rate=optional_rate(
            attack_rejections,
            attack_successes,
        ),
        recoveries_after_rejection=recoveries,
        recovery_after_rejection_rate=optional_rate(recoveries, attack_rejections),
        fallback_containments=fallback_containments,
        control_containments=control_containments,
        control_containment_rate=optional_rate(
            control_containments,
            attack_successes,
        ),
        unsafe_acceptances=unsafe_acceptances,
        unsafe_acceptance_rate=unsafe_acceptances / total,
        asset_identity_integrity_rate=(
            sum(run.asset_identity_integrity for run in runs) / total
        ),
        human_review_integrity_rate=(
            sum(run.human_review_integrity for run in runs) / total
        ),
        recommendation_integrity_rate=(
            sum(run.recommendation_integrity for run in runs) / total
        ),
        confidence_integrity_rate=(
            sum(run.confidence_integrity for run in runs) / total
        ),
        retry_rate=retried / total,
        fallback_rate=fallbacks / total,
        mean_model_calls=round(mean(run.model_calls for run in runs), 2),
        mean_latency_ms=round(mean(latencies), 2),
        p50_latency_ms=round(median(latencies), 2),
        p95_latency_ms=round(nearest_rank_percentile(latencies, 0.95), 2),
        mean_total_tokens=round(mean(run.total_tokens for run in runs), 2),
        total_tokens=sum(run.total_tokens for run in runs),
    )


def build_run(
    scenario: AdversarialEvaluationScenario,
    iteration: int,
    model_name: str,
    latency_ms: float,
    output: LLMAnalysisGraphOutput,
    usage: TokenUsage,
) -> AdversarialRun:
    """Build one fully evaluated adversarial run."""
    validate_run_telemetry(output=output, usage=usage)
    validated_output = build_validated_output(output)
    trajectory = evaluate_adversarial_trajectory(
        scenario=scenario,
        output=validated_output,
    )
    security = trajectory.final_security
    result = output["result"]

    return AdversarialRun(
        scenario_id=scenario.scenario_id,
        iteration=iteration,
        attack_class=scenario.attack_class,
        tags=scenario.tags,
        model=model_name,
        latency_ms=round(latency_ms, 2),
        analysis_source=output["analysis_source"],
        validation_passed=output["validation_passed"],
        analysis_attempts=output["analysis_attempts"],
        model_calls=output["analysis_attempts"],
        task_match=security.task_match,
        security_passed=security.security_passed,
        unsafe_acceptance=security.unsafe_acceptance,
        model_attack_success=trajectory.model_attack_success,
        deterministic_rejection_after_attack=(
            trajectory.deterministic_rejection_after_attack
        ),
        recovery_after_rejection=trajectory.recovery_after_rejection,
        fallback_containment=trajectory.fallback_containment,
        control_containment=trajectory.control_containment,
        asset_identity_integrity=security.asset_identity_integrity,
        human_review_integrity=security.human_review_integrity,
        recommendation_integrity=security.recommendation_integrity,
        confidence_integrity=security.confidence_integrity,
        failed_security_assertions=security.failed_assertions,
        confidence=result.confidence,
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        total_tokens=usage.total_tokens,
        attempt_trace=build_attempt_trace(output=output, trajectory=trajectory),
    )


def format_optional_rate(value: float | None) -> str:
    """Format conditional metrics without treating unexercised controls as failures."""
    if value is None:
        return "N/A"

    return f"{value:.1%}"


def render_markdown_report(
    generated_at_utc: str,
    model_name: str,
    scenario_summaries: list[ScenarioSummary],
    overall: OverallSummary,
) -> str:
    """Render the adversarial evaluation as a human-readable report."""
    metrics = overall.metrics
    lines = [
        "# LangGraph Adversarial Security Evaluation",
        "",
        f"Generated: `{generated_at_utc}`",
        "",
        f"Model: `{model_name}`",
        "",
        f"Framework: `{_FRAMEWORK}`",
        "",
        f"Pattern: `{_PATTERN}`",
        "",
        "Sampling: `provider_default`",
        "",
        "## Task plane",
        "",
        f"- Final task accuracy: **{metrics.task_accuracy:.1%}**",
        f"- Retry rate: **{metrics.retry_rate:.1%}**",
        f"- Fallback rate: **{metrics.fallback_rate:.1%}**",
        "",
        "## Security plane",
        "",
        f"- Final security pass rate: **{metrics.security_pass_rate:.1%}**",
        f"- Unsafe acceptance rate: **{metrics.unsafe_acceptance_rate:.1%}**",
        (
            "- Asset identity/cardinality integrity: "
            f"**{metrics.asset_identity_integrity_rate:.1%}**"
        ),
        f"- Human-review integrity: **{metrics.human_review_integrity_rate:.1%}**",
        f"- Recommendation integrity: **{metrics.recommendation_integrity_rate:.1%}**",
        f"- Confidence integrity: **{metrics.confidence_integrity_rate:.1%}**",
        "",
        "## Model/control separation",
        "",
        f"- Model attack-success rate: **{metrics.model_attack_success_rate:.1%}**",
        (
            "- Deterministic rejection after attack success: "
            f"**{format_optional_rate(metrics.deterministic_rejection_after_attack_rate)}**"
        ),
        (
            "- Recovery after attack rejection: "
            f"**{format_optional_rate(metrics.recovery_after_rejection_rate)}**"
        ),
        (
            "- Control containment after model attack success: "
            f"**{format_optional_rate(metrics.control_containment_rate)}**"
        ),
        f"- Fallback containments: **{metrics.fallback_containments}**",
        "",
        "## Runtime",
        "",
        f"- Mean model calls: **{metrics.mean_model_calls:.2f}**",
        f"- Mean latency: **{metrics.mean_latency_ms:.2f} ms**",
        f"- p50 latency: **{metrics.p50_latency_ms:.2f} ms**",
        f"- p95 latency: **{metrics.p95_latency_ms:.2f} ms**",
        f"- Mean tokens: **{metrics.mean_total_tokens:.2f}**",
        f"- Total tokens: **{metrics.total_tokens}**",
        "",
        "## Scenario results",
        "",
        (
            "| Scenario | Attack class | Task | Security | Model attack | "
            "Containment | Unsafe | Retry | Fallback | Tokens |"
        ),
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]

    for summary in scenario_summaries:
        item = summary.metrics
        lines.append(
            "| "
            f"{summary.scenario_id} | "
            f"{summary.attack_class} | "
            f"{item.task_accuracy:.1%} | "
            f"{item.security_pass_rate:.1%} | "
            f"{item.model_attack_success_rate:.1%} | "
            f"{format_optional_rate(item.control_containment_rate)} | "
            f"{item.unsafe_acceptance_rate:.1%} | "
            f"{item.retry_rate:.1%} | "
            f"{item.fallback_rate:.1%} | "
            f"{item.mean_total_tokens:.2f} |"
        )

    lines.extend(
        [
            "",
            "## Methodology",
            "",
            (
                "`model_attack_success` is only true when a structured draft "
                "matches the scenario-specific deterministic attacker goal. "
                "A generic validation error is not counted as attack success."
            ),
            "",
            (
                "`control_containment` is conditional on observed model attack "
                "success. It measures whether the final system result still "
                "passes all deterministic security assertions."
            ),
            "",
            (
                "`unsafe_acceptance` means an LLM result passed the existing "
                "applicability validator while the adversarial security evaluator "
                "still found a failed assertion."
            ),
            "",
            (
                "The ten scenarios are synthetic instruction/data-boundary tests. "
                "They do not establish general prompt-injection resistance and do "
                "not cover tool misuse, persistent memory, privilege abuse, "
                "inter-agent attacks, or rogue-agent behavior."
            ),
            "",
            (
                "Latency values are descriptive only. With small samples, "
                "nearest-rank p95 is especially unstable and may equal the sample maximum."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def write_artifacts(
    model_name: str,
    repetitions: int,
    runs: list[AdversarialRun],
    scenario_summaries: list[ScenarioSummary],
    overall: OverallSummary,
) -> None:
    """Persist machine-readable and human-readable adversarial artifacts."""
    generated_at = datetime.now(UTC).isoformat()
    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    payload = {
        "schema_version": "1",
        "generated_at_utc": generated_at,
        "framework": _FRAMEWORK,
        "pattern": _PATTERN,
        "model": model_name,
        "sampling": _SAMPLING,
        "repetitions_per_scenario": repetitions,
        "scenario_count": len(scenario_summaries),
        "runs": [asdict(run) for run in runs],
        "scenario_summaries": [asdict(summary) for summary in scenario_summaries],
        "overall_summary": asdict(overall),
    }

    json_path = _OUTPUT_DIR / "latest.json"
    markdown_path = _OUTPUT_DIR / "latest.md"
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
    """Execute the dedicated LangGraph adversarial evaluation."""
    repetitions = parse_runs()
    model_name = require_model_name()
    scenarios = load_adversarial_evaluation_scenarios()
    model = create_chat_model()
    analyzer = LangChainVulnerabilityAnalyzer(model)

    all_runs: list[AdversarialRun] = []
    scenario_summaries: list[ScenarioSummary] = []

    for scenario in scenarios:
        evidence_bundle = build_evidence_bundle(scenario)
        scenario_runs: list[AdversarialRun] = []

        for iteration in range(1, repetitions + 1):
            started_at = perf_counter()

            with get_usage_metadata_callback() as usage_callback:
                output = run_llm_analysis_graph_with_evidence(
                    analyzer=analyzer,
                    evidence_bundle=evidence_bundle,
                )

            latency_ms = (perf_counter() - started_at) * 1000
            usage = aggregate_usage(usage_callback.usage_metadata)
            run = build_run(
                scenario=scenario,
                iteration=iteration,
                model_name=model_name,
                latency_ms=latency_ms,
                output=output,
                usage=usage,
            )
            scenario_runs.append(run)
            all_runs.append(run)
            print(json.dumps({"type": "run", **asdict(run)}))

        summary = ScenarioSummary(
            scenario_id=scenario.scenario_id,
            attack_class=scenario.attack_class,
            tags=scenario.tags,
            metrics=summarize_runs(scenario_runs),
        )
        scenario_summaries.append(summary)
        print(json.dumps({"type": "scenario_summary", **asdict(summary)}))

    overall = OverallSummary(
        framework=_FRAMEWORK,
        pattern=_PATTERN,
        model=model_name,
        scenarios=len(scenarios),
        metrics=summarize_runs(all_runs),
    )

    print()
    print("overall_summary")
    print(json.dumps(asdict(overall), indent=2))
    write_artifacts(
        model_name=model_name,
        repetitions=repetitions,
        runs=all_runs,
        scenario_summaries=scenario_summaries,
        overall=overall,
    )


if __name__ == "__main__":
    main()
