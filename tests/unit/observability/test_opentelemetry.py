"""Tests for the OpenTelemetry-compatible analysis observer backend."""

from collections.abc import Mapping
from types import TracebackType

from agentic_lab.observability import AnalysisExecutionObservation
from agentic_lab.observability.analysis import ANALYSIS_SPAN_NAME, analysis_span_attributes
from agentic_lab.observability.opentelemetry import (
    OpenTelemetryAnalysisObserver,
    SpanAttributeValue,
)


class RecordingSpanScope:
    """Record context-manager entry and exit without an external SDK."""

    def __init__(self) -> None:
        self.entered = False
        self.exited = False

    def __enter__(self) -> object:
        self.entered = True
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        del exc_type, exc_value, traceback
        self.exited = True
        return None


class RecordingTracer:
    """Capture the exact span contract requested by the observer."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, SpanAttributeValue]]] = []
        self.scopes: list[RecordingSpanScope] = []

    def start_as_current_span(
        self,
        name: str,
        *,
        attributes: Mapping[str, SpanAttributeValue],
    ) -> RecordingSpanScope:
        self.calls.append((name, dict(attributes)))
        scope = RecordingSpanScope()
        self.scopes.append(scope)
        return scope


def _observation() -> AnalysisExecutionObservation:
    return AnalysisExecutionObservation(
        framework="llamaindex",
        workflow="llamaindex-workflow",
        analysis_source="oracle_fallback",
        validation_passed=False,
        analysis_attempts=2,
        model_calls=3,
        requires_human_review=True,
    )


def test_observer_emits_exact_safe_span_contract() -> None:
    tracer = RecordingTracer()
    observation = _observation()

    OpenTelemetryAnalysisObserver(tracer).record(observation)

    assert tracer.calls == [
        (
            ANALYSIS_SPAN_NAME,
            analysis_span_attributes(observation),
        )
    ]
    assert len(tracer.scopes) == 1
    assert tracer.scopes[0].entered is True
    assert tracer.scopes[0].exited is True


def test_observer_emits_only_allowlisted_attributes() -> None:
    tracer = RecordingTracer()

    OpenTelemetryAnalysisObserver(tracer).record(_observation())

    _, attributes = tracer.calls[0]
    assert set(attributes) == {
        "agentic.security.framework",
        "agentic.security.workflow",
        "agentic.security.analysis.source",
        "agentic.security.validation.passed",
        "agentic.security.analysis.attempts",
        "agentic.security.model.calls",
        "agentic.security.human_review.required",
    }
    assert all(
        forbidden not in key
        for key in attributes
        for forbidden in (
            "prompt",
            "evidence",
            "rationale",
            "feedback",
            "credential",
            "token",
            "asset_id",
            "cve_id",
        )
    )
