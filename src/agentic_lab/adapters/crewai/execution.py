"""CrewAI Agent/Crew logical execution boundary with safe observability."""

from dataclasses import dataclass
from typing import Protocol

from agentic_lab.adapters.crewai.analyzer import (
    CrewAIAnalysisRunner,
    CrewAIRuntime,
    CrewAIUsage,
    CrewAIVulnerabilityAnalyzer,
)
from agentic_lab.application.evidence import AnalysisEvidenceBundle
from agentic_lab.application.validated_analysis import (
    DEFAULT_MAX_ANALYSIS_ATTEMPTS,
    ValidatedAnalysisOutput,
    run_validated_analysis,
)
from agentic_lab.observability import AnalysisExecutionObservation
from agentic_lab.observability.observer import (
    NULL_ANALYSIS_OBSERVER,
    AnalysisObserver,
)


class _UsageAwareCrewAIRunner(CrewAIAnalysisRunner, Protocol):
    """CrewAI runner that also exposes normalized delta usage."""

    def consume_usage(self) -> CrewAIUsage:
        """Return usage accumulated since the previous consumption."""
        ...


@dataclass(frozen=True, slots=True)
class CrewAIAgentCrewExecution:
    """Return one complete validated Agent/Crew execution and its usage."""

    output: ValidatedAnalysisOutput
    usage: CrewAIUsage


def _usage_is_clean(usage: CrewAIUsage) -> bool:
    """Return whether no unconsumed CrewAI usage remains."""
    return (
        usage.input_tokens == 0
        and usage.output_tokens == 0
        and usage.total_tokens == 0
        and usage.model_calls == 0
    )


class CrewAIAgentCrewRuntime:
    """Own one complete validated Agent/Crew execution boundary."""

    def __init__(
        self,
        runner: _UsageAwareCrewAIRunner | None = None,
        observer: AnalysisObserver = NULL_ANALYSIS_OBSERVER,
    ) -> None:
        """Configure the attempt runner and completed-execution observer."""
        self._runner = runner if runner is not None else CrewAIRuntime()
        self._observer = observer

    def run(
        self,
        evidence_bundle: AnalysisEvidenceBundle,
        max_attempts: int = DEFAULT_MAX_ANALYSIS_ATTEMPTS,
    ) -> CrewAIAgentCrewExecution:
        """Execute the validated Agent/Crew loop and emit one final observation."""
        stale_usage = self._runner.consume_usage()
        if not _usage_is_clean(stale_usage):
            raise RuntimeError(
                "CrewAI Agent/Crew usage telemetry was not clean before logical execution"
            )

        analyzer = CrewAIVulnerabilityAnalyzer(self._runner)

        try:
            output = run_validated_analysis(
                analyzer=analyzer,
                evidence_bundle=evidence_bundle,
                max_attempts=max_attempts,
            )
        except Exception:
            self._runner.consume_usage()
            raise

        usage = self._runner.consume_usage()
        if usage.model_calls < output.analysis_attempts:
            raise RuntimeError(
                "CrewAI Agent/Crew reported fewer model calls than analysis attempts"
            )

        self._observer.record(
            AnalysisExecutionObservation(
                framework="crewai",
                workflow="crewai-agent-crew",
                analysis_source=output.analysis_source,
                validation_passed=output.validation_passed,
                analysis_attempts=output.analysis_attempts,
                model_calls=usage.model_calls,
                requires_human_review=output.result.requires_human_review,
            )
        )

        return CrewAIAgentCrewExecution(
            output=output,
            usage=usage,
        )
