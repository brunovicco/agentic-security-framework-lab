"""Observer port for completed logical analysis executions."""

from typing import Protocol

from agentic_lab.observability.analysis import AnalysisExecutionObservation


class AnalysisObserver(Protocol):
    """Receive one observation after a logical analysis execution completes."""

    def record(self, observation: AnalysisExecutionObservation) -> None:
        """Record one completed logical execution observation."""
        ...


class NullAnalysisObserver:
    """Default observer that deliberately emits no telemetry."""

    def record(self, observation: AnalysisExecutionObservation) -> None:
        """Ignore the completed observation without side effects."""
        del observation


NULL_ANALYSIS_OBSERVER = NullAnalysisObserver()
