"""Agno structured vulnerability-analysis adapter."""

from dataclasses import dataclass
from typing import Literal, Protocol, cast

from agno.agent import Agent, RunOutput
from agno.metrics import RunMetrics
from agno.models.openai import OpenAIChat

from agentic_lab.application.analysis_prompt import (
    SECURITY_ANALYSIS_SYSTEM_PROMPT,
    build_security_analysis_user_prompt,
)
from agentic_lab.application.contracts import LLMAnalysisDraft
from agentic_lab.application.evidence import (
    AssetInventoryItem,
    VulnerabilityEvidence,
)


@dataclass(frozen=True, slots=True)
class AgnoUsage:
    """Capture accumulated Agno LLM telemetry since the last consumption."""

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    model_calls: int = 0


class AgnoAnalysisRunner(Protocol):
    """Execute one structured Agno analysis attempt."""

    def run(self, system_prompt: str, user_prompt: str) -> LLMAnalysisDraft:
        """Return a validated structured LLM draft."""
        ...


class _StructuredAgnoAgent(Protocol):
    """Minimum non-streaming Agent surface used by this adapter."""

    def run(
        self,
        input: str,
        *,
        stream: Literal[False] = False,
    ) -> RunOutput:
        """Execute one non-streaming agent run."""
        ...


def normalize_agno_model_name(model_name: str) -> str:
    """Translate the shared provider:model identifier to Agno OpenAI syntax."""
    provider, separator, model = model_name.partition(":")

    if not separator:
        return model_name

    if provider != "openai" or not model:
        raise ValueError("Agno OpenAI adapter requires an openai:model identifier")

    return model


def _create_model(model_name: str) -> OpenAIChat:
    """Create Agno's OpenAI model without overriding provider-default sampling."""
    return OpenAIChat(id=normalize_agno_model_name(model_name))


def _create_agent(model_name: str, system_prompt: str) -> _StructuredAgnoAgent:
    """Create a minimal structured Agno Agent for vulnerability reasoning."""
    return cast(
        _StructuredAgnoAgent,
        Agent(
            model=_create_model(model_name),
            system_message=system_prompt,
            output_schema=LLMAnalysisDraft,
            structured_outputs=True,
            parse_response=True,
            add_history_to_context=False,
            retries=0,
            telemetry=False,
            tools=None,
            db=None,
            store_events=False,
            markdown=False,
        ),
    )


def _usage_from_metrics(metrics: RunMetrics | None) -> AgnoUsage:
    """Translate one isolated Agno run metric into benchmark telemetry."""
    if metrics is None:
        raise RuntimeError("Agno run did not provide token metrics")

    if metrics.input_tokens <= 0:
        raise RuntimeError("Agno run reported no input tokens")
    if metrics.output_tokens <= 0:
        raise RuntimeError("Agno run reported no output tokens")
    if metrics.total_tokens <= 0:
        raise RuntimeError("Agno run reported no total tokens")

    return AgnoUsage(
        input_tokens=metrics.input_tokens,
        output_tokens=metrics.output_tokens,
        total_tokens=metrics.total_tokens,
        model_calls=1,
    )


def _add_usage(current: AgnoUsage, new: AgnoUsage) -> AgnoUsage:
    """Accumulate isolated Agno run metrics across bounded analysis attempts."""
    return AgnoUsage(
        input_tokens=current.input_tokens + new.input_tokens,
        output_tokens=current.output_tokens + new.output_tokens,
        total_tokens=current.total_tokens + new.total_tokens,
        model_calls=current.model_calls + new.model_calls,
    )


class AgnoRuntime:
    """Execute structured vulnerability reasoning through a minimal Agno Agent."""

    def __init__(
        self,
        model_name: str,
        system_prompt: str = SECURITY_ANALYSIS_SYSTEM_PROMPT,
    ) -> None:
        """Create an isolated Agno agent and empty benchmark usage accumulator."""
        self._system_prompt = system_prompt
        self._agent = _create_agent(
            model_name=model_name,
            system_prompt=system_prompt,
        )
        self._usage = AgnoUsage()

    def consume_usage(self) -> AgnoUsage:
        """Return accumulated usage and reset it for the next benchmark run."""
        usage = self._usage
        self._usage = AgnoUsage()
        return usage

    def run(self, system_prompt: str, user_prompt: str) -> LLMAnalysisDraft:
        """Execute one provider-structured Agno analysis attempt."""
        if system_prompt != self._system_prompt:
            raise ValueError("Agno runtime system prompt does not match its configured boundary")

        response = self._agent.run(user_prompt, stream=False)

        if not isinstance(response.content, LLMAnalysisDraft):
            raise RuntimeError("Agno structured output did not return LLMAnalysisDraft")

        usage = _usage_from_metrics(response.metrics)
        self._usage = _add_usage(self._usage, usage)
        return response.content


class AgnoVulnerabilityAnalyzer:
    """Produce structured vulnerability reasoning through an Agno runner."""

    def __init__(self, runner: AgnoAnalysisRunner) -> None:
        """Store the framework runtime behind the application analyzer port."""
        self._runner = runner

    def analyze(
        self,
        vulnerability: VulnerabilityEvidence,
        assets: tuple[AssetInventoryItem, ...],
        feedback: str | None = None,
    ) -> LLMAnalysisDraft:
        """Analyze vulnerability evidence against asset inventory."""
        return self._runner.run(
            system_prompt=SECURITY_ANALYSIS_SYSTEM_PROMPT,
            user_prompt=build_security_analysis_user_prompt(
                vulnerability=vulnerability,
                assets=assets,
                feedback=feedback,
            ),
        )
