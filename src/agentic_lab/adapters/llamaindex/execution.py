"""Logical execution boundary for observed LlamaIndex Workflow runs."""

from typing import Protocol

from agentic_lab.adapters.llamaindex.workflow import (
    LlamaIndexWorkflowExecution,
    LlamaIndexWorkflowRuntime,
)
from agentic_lab.application.evidence import AnalysisEvidenceBundle
from agentic_lab.application.validated_analysis import DEFAULT_MAX_ANALYSIS_ATTEMPTS
from agentic_lab.observability.analysis import AnalysisExecutionObservation
from agentic_lab.observability.observer import (
    NULL_ANALYSIS_OBSERVER,
    AnalysisObserver,
)


class LlamaIndexWorkflowRunner(Protocol):
    """Execute one complete validated LlamaIndex Workflow."""

    async def arun(
        self,
        evidence_bundle: AnalysisEvidenceBundle,
        max_attempts: int = DEFAULT_MAX_ANALYSIS_ATTEMPTS,
    ) -> LlamaIndexWorkflowExecution:
        """Execute one asynchronous logical Workflow run."""
        ...

    def run(
        self,
        evidence_bundle: AnalysisEvidenceBundle,
        max_attempts: int = DEFAULT_MAX_ANALYSIS_ATTEMPTS,
    ) -> LlamaIndexWorkflowExecution:
        """Execute one synchronous logical Workflow run."""
        ...


class LlamaIndexObservedWorkflowRuntime:
    """Emit one safe observation for each completed LlamaIndex Workflow run."""

    def __init__(
        self,
        *,
        runtime: LlamaIndexWorkflowRunner | None = None,
        observer: AnalysisObserver = NULL_ANALYSIS_OBSERVER,
    ) -> None:
        """Wrap the native Workflow runtime without coupling it to telemetry backends."""
        self._runtime = runtime if runtime is not None else LlamaIndexWorkflowRuntime()
        self._observer = observer

    def _observe(self, execution: LlamaIndexWorkflowExecution) -> LlamaIndexWorkflowExecution:
        output = execution.output
        usage = execution.usage

        if usage.model_calls < output.analysis_attempts:
            raise RuntimeError(
                "LlamaIndex usage exposed fewer model calls than analysis attempts"
            )

        self._observer.record(
            AnalysisExecutionObservation(
                framework="llamaindex",
                workflow="llamaindex-workflow",
                analysis_source=output.analysis_source,
                validation_passed=output.validation_passed,
                analysis_attempts=output.analysis_attempts,
                model_calls=usage.model_calls,
                requires_human_review=output.result.requires_human_review,
            )
        )
        return execution

    async def arun(
        self,
        evidence_bundle: AnalysisEvidenceBundle,
        max_attempts: int = DEFAULT_MAX_ANALYSIS_ATTEMPTS,
    ) -> LlamaIndexWorkflowExecution:
        """Run asynchronously and observe only a completed logical execution."""
        execution = await self._runtime.arun(
            evidence_bundle=evidence_bundle,
            max_attempts=max_attempts,
        )
        return self._observe(execution)

    def run(
        self,
        evidence_bundle: AnalysisEvidenceBundle,
        max_attempts: int = DEFAULT_MAX_ANALYSIS_ATTEMPTS,
    ) -> LlamaIndexWorkflowExecution:
        """Run synchronously and observe only a completed logical execution."""
        execution = self._runtime.run(
            evidence_bundle=evidence_bundle,
            max_attempts=max_attempts,
        )
        return self._observe(execution)
