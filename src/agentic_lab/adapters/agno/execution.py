"""Logical execution boundary for observed Agno Workflow runs."""

from typing import Protocol

from agentic_lab.adapters.agno.workflow import AgnoWorkflowExecution, AgnoWorkflowRuntime
from agentic_lab.application.evidence import AnalysisEvidenceBundle
from agentic_lab.application.validated_analysis import DEFAULT_MAX_ANALYSIS_ATTEMPTS
from agentic_lab.observability.analysis import AnalysisExecutionObservation
from agentic_lab.observability.observer import NULL_ANALYSIS_OBSERVER, AnalysisObserver


class AgnoWorkflowRunner(Protocol):
    """Execute one complete validated Agno Workflow."""

    def run(
        self,
        evidence_bundle: AnalysisEvidenceBundle,
        max_attempts: int = DEFAULT_MAX_ANALYSIS_ATTEMPTS,
    ) -> AgnoWorkflowExecution:
        """Execute one logical Workflow run."""
        ...


class AgnoObservedWorkflowRuntime:
    """Emit one safe observation for each completed Agno Workflow run."""

    def __init__(
        self,
        *,
        runtime: AgnoWorkflowRunner | None = None,
        observer: AnalysisObserver = NULL_ANALYSIS_OBSERVER,
    ) -> None:
        """Wrap the native Workflow runtime without coupling it to telemetry backends."""
        self._runtime = runtime if runtime is not None else AgnoWorkflowRuntime()
        self._observer = observer

    def run(
        self,
        evidence_bundle: AnalysisEvidenceBundle,
        max_attempts: int = DEFAULT_MAX_ANALYSIS_ATTEMPTS,
    ) -> AgnoWorkflowExecution:
        """Run and observe only a completed logical execution."""
        execution = self._runtime.run(
            evidence_bundle=evidence_bundle,
            max_attempts=max_attempts,
        )
        output = execution.output
        usage = execution.usage

        if usage.model_calls < output.analysis_attempts:
            raise RuntimeError("Agno usage exposed fewer model calls than analysis attempts")

        self._observer.record(
            AnalysisExecutionObservation(
                framework="agno",
                workflow="agno-workflow",
                analysis_source=output.analysis_source,
                validation_passed=output.validation_passed,
                analysis_attempts=output.analysis_attempts,
                model_calls=usage.model_calls,
                requires_human_review=output.result.requires_human_review,
            )
        )
        return execution
