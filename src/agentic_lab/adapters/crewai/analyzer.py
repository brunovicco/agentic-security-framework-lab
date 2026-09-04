"""CrewAI structured vulnerability-analysis adapter."""

from dataclasses import dataclass
from typing import Protocol, cast

from crewai import Agent, Crew, Process, Task

from agentic_lab.adapters.crewai.model import create_crewai_llm
from agentic_lab.application.analysis_prompt import (
    SECURITY_ANALYSIS_SYSTEM_PROMPT,
    build_security_analysis_user_prompt,
)
from agentic_lab.application.contracts import LLMAnalysisDraft
from agentic_lab.application.evidence import (
    AssetInventoryItem,
    EvidenceDocument,
    VulnerabilityEvidence,
)

CREWAI_SECURITY_SYSTEM_PROMPT = SECURITY_ANALYSIS_SYSTEM_PROMPT


@dataclass(frozen=True, slots=True)
class CrewAIUsage:
    """Capture framework-reported LLM usage across CrewAI analysis attempts."""

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    model_calls: int = 0

    def plus(self, other: "CrewAIUsage") -> "CrewAIUsage":
        """Return the field-wise sum of two usage observations."""
        return CrewAIUsage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            total_tokens=self.total_tokens + other.total_tokens,
            model_calls=self.model_calls + other.model_calls,
        )

    def delta_since(self, baseline: "CrewAIUsage") -> "CrewAIUsage":
        """Return usage accumulated since a previously observed cumulative baseline."""
        deltas = (
            self.input_tokens - baseline.input_tokens,
            self.output_tokens - baseline.output_tokens,
            self.total_tokens - baseline.total_tokens,
            self.model_calls - baseline.model_calls,
        )

        if any(value < 0 for value in deltas):
            raise RuntimeError("CrewAI usage telemetry counters decreased unexpectedly")

        return CrewAIUsage(
            input_tokens=deltas[0],
            output_tokens=deltas[1],
            total_tokens=deltas[2],
            model_calls=deltas[3],
        )


class CrewAIAnalysisRunner(Protocol):
    """Execute one structured CrewAI analysis task."""

    def run(self, task_description: str) -> LLMAnalysisDraft:
        """Run the CrewAI task and return validated structured output."""
        ...


class _CrewKickoff(Protocol):
    """Narrow typed boundary for CrewAI's partially typed kickoff method."""

    def kickoff(self) -> object:
        """Execute the crew synchronously."""
        ...


class _UsageMetrics(Protocol):
    """Minimum CrewAI usage surface required for benchmark telemetry."""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    successful_requests: int


class _CrewExecutionOutput(Protocol):
    """Minimum Crew output surface required after execution."""

    token_usage: _UsageMetrics


class _StructuredTaskOutput(Protocol):
    """Minimum structured output surface required from a CrewAI task."""

    pydantic: object | None


class _OutputTask(Protocol):
    """Minimum task surface required after CrewAI execution."""

    output: _StructuredTaskOutput | None


def build_crewai_analysis_task_description(
    vulnerability: VulnerabilityEvidence,
    assets: tuple[AssetInventoryItem, ...],
    feedback: str | None = None,
    documents: tuple[EvidenceDocument, ...] = (),
) -> str:
    """Build the shared CrewAI user prompt for one analysis attempt."""
    return build_security_analysis_user_prompt(
        vulnerability=vulnerability,
        assets=assets,
        feedback=feedback,
        documents=documents,
    )


class CrewAIRuntime:
    """Execute structured vulnerability reasoning through CrewAI."""

    def __init__(self, model_name: str) -> None:
        """Configure CrewAI through the gateway while retaining transitional metadata input."""
        _ = model_name
        self._llm = create_crewai_llm()
        self._latest_usage = CrewAIUsage()
        self._consumed_usage = CrewAIUsage()

    def consume_usage(self) -> CrewAIUsage:
        """Return usage accumulated since the previous consumption."""
        usage = self._latest_usage.delta_since(self._consumed_usage)
        self._consumed_usage = self._latest_usage
        return usage

    def run(self, task_description: str) -> LLMAnalysisDraft:
        """Execute a single-agent CrewAI task with Pydantic output validation."""
        analyst = Agent(
            role="Security Vulnerability Analyst",
            goal=(
                "Determine vulnerability applicability using only supplied evidence and "
                "return a structured analysis."
            ),
            backstory=CREWAI_SECURITY_SYSTEM_PROMPT,
            llm=self._llm,
            allow_delegation=False,
            verbose=False,
        )

        task = Task(
            description=task_description,
            expected_output=(
                "A structured vulnerability analysis matching the LLMAnalysisDraft schema."
            ),
            agent=analyst,
            output_pydantic=LLMAnalysisDraft,
        )

        crew = Crew(
            agents=[analyst],
            tasks=[task],
            process=Process.sequential,
            verbose=False,
        )

        execution_output = cast(_CrewExecutionOutput, cast(_CrewKickoff, crew).kickoff())
        usage = execution_output.token_usage
        self._latest_usage = CrewAIUsage(
            input_tokens=usage.prompt_tokens,
            output_tokens=usage.completion_tokens,
            total_tokens=usage.total_tokens,
            model_calls=usage.successful_requests,
        )

        task_output = cast(_OutputTask, task).output

        if task_output is None or task_output.pydantic is None:
            raise RuntimeError("CrewAI did not return the required structured analysis")

        return LLMAnalysisDraft.model_validate(task_output.pydantic)


class CrewAIVulnerabilityAnalyzer:
    """Produce structured vulnerability reasoning through a CrewAI runner."""

    def __init__(self, runner: CrewAIAnalysisRunner) -> None:
        """Store the framework runtime behind a narrow adapter boundary."""
        self._runner = runner

    def analyze(
        self,
        vulnerability: VulnerabilityEvidence,
        assets: tuple[AssetInventoryItem, ...],
        feedback: str | None = None,
        documents: tuple[EvidenceDocument, ...] = (),
    ) -> LLMAnalysisDraft:
        """Analyze vulnerability evidence against asset inventory and documents."""
        return self._runner.run(
            build_crewai_analysis_task_description(
                vulnerability=vulnerability,
                assets=assets,
                feedback=feedback,
                documents=documents,
            )
        )
