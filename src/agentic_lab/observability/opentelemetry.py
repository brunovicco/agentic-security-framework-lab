"""OpenTelemetry-compatible backend for safe logical analysis observations."""

from collections.abc import Mapping
from types import TracebackType
from typing import Protocol

from agentic_lab.observability.analysis import (
    ANALYSIS_SPAN_NAME,
    AnalysisExecutionObservation,
    analysis_span_attributes,
)

SpanAttributeValue = str | bool | int


class AnalysisSpanScope(Protocol):
    """Minimal context-manager contract required to delimit one analysis span."""

    def __enter__(self) -> object:
        """Enter the span scope."""
        ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        """Exit the span scope."""
        ...


class AnalysisTracer(Protocol):
    """Minimal tracer surface used by the project-owned observer."""

    def start_as_current_span(
        self,
        name: str,
        *,
        attributes: Mapping[str, SpanAttributeValue],
    ) -> AnalysisSpanScope:
        """Start one current span with the supplied safe attributes."""
        ...


class OpenTelemetryAnalysisObserver:
    """Convert one safe logical observation into one OpenTelemetry-compatible span."""

    def __init__(self, tracer: AnalysisTracer) -> None:
        """Use a tracer supplied by the deployment composition root."""
        self._tracer = tracer

    def record(self, observation: AnalysisExecutionObservation) -> None:
        """Emit exactly one content-free span for a completed logical execution."""
        attributes = analysis_span_attributes(observation)
        with self._tracer.start_as_current_span(
            ANALYSIS_SPAN_NAME,
            attributes=attributes,
        ):
            pass
