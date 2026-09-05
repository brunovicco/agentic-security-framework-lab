"""Safe framework-neutral telemetry for one validated analysis execution."""

from dataclasses import dataclass
from typing import Literal

FrameworkName = Literal["langgraph", "crewai", "llamaindex", "agno"]
WorkflowName = Literal[
    "langgraph-evaluator-optimizer",
    "crewai-agent-crew",
    "crewai-flow",
    "llamaindex-workflow",
    "agno-workflow",
]
AnalysisSource = Literal["llm", "oracle_fallback"]

ANALYSIS_SPAN_NAME = "validated_analysis"


@dataclass(frozen=True, slots=True)
class AnalysisExecutionObservation:
    """Describe one logical validated-analysis execution without content-bearing data."""

    framework: FrameworkName
    workflow: WorkflowName
    analysis_source: AnalysisSource
    validation_passed: bool
    analysis_attempts: int
    model_calls: int
    requires_human_review: bool

    def __post_init__(self) -> None:
        """Reject impossible telemetry before it reaches an observability backend."""
        if self.analysis_attempts < 1:
            raise ValueError("analysis_attempts must be at least 1")
        if self.model_calls < self.analysis_attempts:
            raise ValueError("model_calls must be at least analysis_attempts")
        if self.analysis_source == "llm" and not self.validation_passed:
            raise ValueError("llm final source requires deterministic validation to pass")
        if self.analysis_source == "oracle_fallback" and self.validation_passed:
            raise ValueError("oracle fallback cannot claim LLM draft validation passed")


def analysis_span_attributes(
    observation: AnalysisExecutionObservation,
) -> dict[str, str | bool | int]:
    """Return the deliberately minimal attribute set allowed on analysis spans."""
    return {
        "agentic.security.framework": observation.framework,
        "agentic.security.workflow": observation.workflow,
        "agentic.security.analysis.source": observation.analysis_source,
        "agentic.security.validation.passed": observation.validation_passed,
        "agentic.security.analysis.attempts": observation.analysis_attempts,
        "agentic.security.model.calls": observation.model_calls,
        "agentic.security.human_review.required": observation.requires_human_review,
    }
