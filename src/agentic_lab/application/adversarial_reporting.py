"""Framework-neutral reporting contracts for adversarial evaluations."""

import math
from dataclasses import dataclass
from statistics import mean, median

from agentic_lab.application.adversarial_evaluation import (
    AdversarialTrajectoryEvaluation,
)
from agentic_lab.application.validated_analysis import (
    AnalysisSource,
    ValidatedAnalysisOutput,
)


@dataclass(frozen=True, slots=True)
class AdversarialRuntimeUsage:
    """Represent standardized provider usage for one adversarial execution."""

    model_calls: int
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
    """Capture one adversarial execution independent of framework implementation."""

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
    """Aggregate one framework's complete adversarial evaluation."""

    framework: str
    pattern: str
    model: str
    scenarios: int
    metrics: AdversarialSummary


def build_attempt_trace(
    output: ValidatedAnalysisOutput,
    trajectory: AdversarialTrajectoryEvaluation,
) -> tuple[AttemptTraceRecord, ...]:
    """Join raw attempt evidence to deterministic attack classifications."""
    raw_attempts = output.attempt_trace

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
                    (assessment.asset_id, assessment.status) for assessment in raw.draft.assets
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
    output: ValidatedAnalysisOutput,
    usage: AdversarialRuntimeUsage,
) -> None:
    """Fail closed when attempt or provider telemetry is incomplete."""
    if output.analysis_attempts < 1:
        raise RuntimeError("Adversarial execution reported no analysis attempts")

    if len(output.attempt_trace) != output.analysis_attempts:
        raise RuntimeError("Attempt trace length does not match analysis_attempts")

    if usage.model_calls < output.analysis_attempts:
        raise RuntimeError("Model call telemetry is lower than analysis attempts")

    if usage.input_tokens <= 0 or usage.output_tokens <= 0 or usage.total_tokens <= 0:
        raise RuntimeError("Adversarial execution returned incomplete token telemetry")

    if usage.input_tokens + usage.output_tokens != usage.total_tokens:
        raise RuntimeError("Adversarial token telemetry does not add up")


def optional_rate(numerator: int, denominator: int) -> float | None:
    """Return a rate only when its conditional denominator was exercised."""
    if denominator == 0:
        return None

    return numerator / denominator


def nearest_rank_percentile(values: list[float], percentile: float) -> float:
    """Calculate a percentile using nearest-rank semantics."""
    if not values:
        raise ValueError("Percentile requires at least one value")

    if not 0 < percentile <= 1:
        raise ValueError("Percentile must be greater than 0 and at most 1")

    ordered = sorted(values)
    rank = math.ceil(percentile * len(ordered))
    return ordered[rank - 1]


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
