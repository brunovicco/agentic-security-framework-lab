"""Offline tests for framework-neutral adversarial reporting."""

import pytest

from agentic_lab.application.adversarial_reporting import (
    AdversarialRun,
    AdversarialRuntimeUsage,
    optional_rate,
    summarize_runs,
    validate_run_telemetry,
)
from agentic_lab.application.contracts import (
    AnalysisResult,
    AssetAssessment,
    LLMAnalysisDraft,
)
from agentic_lab.application.validated_analysis import (
    AnalysisAttemptEvidence,
    ValidatedAnalysisOutput,
)


def _validated_output(*, attempts: int = 1) -> ValidatedAnalysisOutput:
    assessment = AssetAssessment(
        asset_id="asset-01",
        status="affected",
        rationale="Deterministic test rationale.",
    )
    draft = LLMAnalysisDraft(
        assets=(assessment,),
        recommendation="Patch the affected asset.",
        confidence=0.9,
    )
    trace = tuple(
        AnalysisAttemptEvidence(
            attempt=attempt,
            input_feedback=None if attempt == 1 else "retry feedback",
            draft=draft,
            validation_passed=attempt == attempts,
            validation_reason="test",
            validation_feedback="" if attempt == attempts else "retry feedback",
        )
        for attempt in range(1, attempts + 1)
    )
    result = AnalysisResult(
        cve_id="CVE-2026-9999",
        severity="critical",
        assets=(assessment,),
        recommendation=draft.recommendation,
        confidence=draft.confidence,
        evidence=("fixture:test",),
        requires_human_review=True,
    )
    return ValidatedAnalysisOutput(
        result=result,
        analysis_source="llm",
        validation_passed=True,
        validation_reason="test",
        analysis_attempts=attempts,
        attempt_trace=trace,
    )


def _run(
    *,
    model_attack_success: bool,
    deterministic_rejection_after_attack: bool = False,
    recovery_after_rejection: bool = False,
    control_containment: bool = False,
    analysis_attempts: int = 1,
) -> AdversarialRun:
    return AdversarialRun(
        scenario_id="adv-test",
        iteration=1,
        attack_class="goal_hijack",
        tags=("adversarial",),
        model="openai:test",
        latency_ms=100.0,
        analysis_source="llm",
        validation_passed=True,
        analysis_attempts=analysis_attempts,
        model_calls=analysis_attempts,
        task_match=True,
        security_passed=True,
        unsafe_acceptance=False,
        model_attack_success=model_attack_success,
        deterministic_rejection_after_attack=deterministic_rejection_after_attack,
        recovery_after_rejection=recovery_after_rejection,
        fallback_containment=False,
        control_containment=control_containment,
        asset_identity_integrity=True,
        human_review_integrity=True,
        recommendation_integrity=True,
        confidence_integrity=True,
        failed_security_assertions=(),
        confidence=0.9,
        input_tokens=400,
        output_tokens=200,
        total_tokens=600,
        attempt_trace=(),
    )


def _usage(*, model_calls: int = 1, total_tokens: int = 600) -> AdversarialRuntimeUsage:
    return AdversarialRuntimeUsage(
        model_calls=model_calls,
        input_tokens=400,
        output_tokens=200,
        total_tokens=total_tokens,
    )


def test_validate_run_telemetry_accepts_complete_attempt_and_token_evidence() -> None:
    validate_run_telemetry(
        output=_validated_output(attempts=2),
        usage=_usage(model_calls=2),
    )


def test_validate_run_telemetry_fails_closed_for_inconsistent_tokens() -> None:
    with pytest.raises(RuntimeError, match="does not add up"):
        validate_run_telemetry(
            output=_validated_output(),
            usage=_usage(total_tokens=601),
        )


def test_validate_run_telemetry_fails_closed_for_missing_attempt_trace() -> None:
    valid = _validated_output(attempts=2)
    output = ValidatedAnalysisOutput(
        result=valid.result,
        analysis_source=valid.analysis_source,
        validation_passed=valid.validation_passed,
        validation_reason=valid.validation_reason,
        analysis_attempts=valid.analysis_attempts,
        attempt_trace=valid.attempt_trace[:1],
    )

    with pytest.raises(RuntimeError, match="trace length"):
        validate_run_telemetry(
            output=output,
            usage=_usage(model_calls=2),
        )


def test_validate_run_telemetry_rejects_missing_model_calls() -> None:
    with pytest.raises(RuntimeError, match="lower than analysis attempts"):
        validate_run_telemetry(
            output=_validated_output(attempts=2),
            usage=_usage(model_calls=1),
        )


def test_conditional_rates_are_none_when_attack_control_was_not_exercised() -> None:
    assert optional_rate(0, 0) is None

    summary = summarize_runs([_run(model_attack_success=False)])

    assert summary.model_attack_success_rate == 0.0
    assert summary.deterministic_rejection_after_attack_rate is None
    assert summary.recovery_after_rejection_rate is None
    assert summary.control_containment_rate is None


def test_summary_separates_attack_success_from_successful_containment() -> None:
    runs = [
        _run(
            model_attack_success=True,
            deterministic_rejection_after_attack=True,
            recovery_after_rejection=True,
            control_containment=True,
            analysis_attempts=2,
        ),
        _run(model_attack_success=False),
    ]

    summary = summarize_runs(runs)

    assert summary.task_accuracy == 1.0
    assert summary.security_pass_rate == 1.0
    assert summary.model_attack_success_rate == 0.5
    assert summary.deterministic_rejection_after_attack_rate == 1.0
    assert summary.recovery_after_rejection_rate == 1.0
    assert summary.control_containment_rate == 1.0
    assert summary.unsafe_acceptance_rate == 0.0
    assert summary.retry_rate == 0.5
    assert summary.mean_model_calls == 1.5
    assert summary.mean_total_tokens == 600.0
