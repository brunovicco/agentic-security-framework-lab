"""Tests for framework-neutral validated-analysis telemetry."""

import pytest

from agentic_lab.observability.analysis import (
    ANALYSIS_SPAN_NAME,
    AnalysisExecutionObservation,
    AnalysisSource,
    FrameworkName,
    WorkflowName,
    analysis_span_attributes,
)


def _observation(
    *,
    framework: FrameworkName = "langgraph",
    workflow: WorkflowName = "langgraph-evaluator-optimizer",
    analysis_source: AnalysisSource = "llm",
    validation_passed: bool = True,
    analysis_attempts: int = 1,
    model_calls: int = 1,
    requires_human_review: bool = True,
) -> AnalysisExecutionObservation:
    return AnalysisExecutionObservation(
        framework=framework,
        workflow=workflow,
        analysis_source=analysis_source,
        validation_passed=validation_passed,
        analysis_attempts=analysis_attempts,
        model_calls=model_calls,
        requires_human_review=requires_human_review,
    )


def test_analysis_observation_exposes_only_safe_operational_attributes() -> None:
    observation = _observation()

    assert ANALYSIS_SPAN_NAME == "validated_analysis"
    assert analysis_span_attributes(observation) == {
        "agentic.security.framework": "langgraph",
        "agentic.security.workflow": "langgraph-evaluator-optimizer",
        "agentic.security.analysis.source": "llm",
        "agentic.security.validation.passed": True,
        "agentic.security.analysis.attempts": 1,
        "agentic.security.model.calls": 1,
        "agentic.security.human_review.required": True,
    }


def test_analysis_observation_rejects_zero_attempts() -> None:
    with pytest.raises(ValueError, match="analysis_attempts must be at least 1"):
        _observation(analysis_attempts=0)


def test_analysis_observation_rejects_fewer_model_calls_than_attempts() -> None:
    with pytest.raises(ValueError, match="model_calls must be at least analysis_attempts"):
        _observation(analysis_attempts=2, model_calls=1)


def test_analysis_observation_rejects_invalid_llm_final_state() -> None:
    with pytest.raises(ValueError, match="llm final source requires"):
        _observation(validation_passed=False)


def test_analysis_observation_rejects_invalid_fallback_final_state() -> None:
    with pytest.raises(ValueError, match="oracle fallback cannot claim"):
        _observation(analysis_source="oracle_fallback", validation_passed=True)


def test_analysis_observation_accepts_valid_oracle_fallback_state() -> None:
    observation = _observation(
        analysis_source="oracle_fallback",
        validation_passed=False,
        analysis_attempts=2,
        model_calls=2,
        requires_human_review=False,
    )

    assert observation.analysis_source == "oracle_fallback"
    assert observation.validation_passed is False
