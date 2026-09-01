"""LlamaIndex structured vulnerability-analysis adapter."""

from dataclasses import dataclass
from typing import Protocol, cast

from llama_index.core.base.llms.types import ChatMessage, MessageRole
from llama_index.core.callbacks import CallbackManager, TokenCountingHandler
from llama_index.core.prompts import ChatPromptTemplate
from llama_index.llms.openai import OpenAI
from pydantic import BaseModel

from agentic_lab.application.analysis_prompt import (
    SECURITY_ANALYSIS_SYSTEM_PROMPT,
    build_security_analysis_user_prompt,
)
from agentic_lab.application.contracts import LLMAnalysisDraft
from agentic_lab.application.evidence import (
    AssetInventoryItem,
    VulnerabilityEvidence,
)

LLAMAINDEX_PROVIDER_DEFAULT_TEMPERATURE = 1.0


@dataclass(frozen=True, slots=True)
class LlamaIndexUsage:
    """Capture per-consumption LlamaIndex LLM telemetry."""

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    model_calls: int = 0


class LlamaIndexAnalysisRunner(Protocol):
    """Execute one structured LlamaIndex analysis attempt."""

    def run(self, system_prompt: str, user_prompt: str) -> LLMAnalysisDraft:
        """Return a validated structured LLM draft."""
        ...


class _StructuredPredictLLM(Protocol):
    """Minimum structured prediction surface used by this adapter."""

    def structured_predict(
        self,
        output_cls: type[BaseModel],
        prompt: ChatPromptTemplate,
    ) -> BaseModel:
        """Return one Pydantic structured prediction."""
        ...


class _TokenCounter(Protocol):
    """Minimum token-counting surface used for benchmark telemetry."""

    @property
    def prompt_llm_token_count(self) -> int:
        """Return cumulative prompt tokens."""
        ...

    @property
    def completion_llm_token_count(self) -> int:
        """Return cumulative completion tokens."""
        ...

    @property
    def total_llm_token_count(self) -> int:
        """Return cumulative total LLM tokens."""
        ...

    @property
    def llm_token_counts(self) -> list[object]:
        """Return one usage event per observed LLM callback."""
        ...

    def reset_counts(self) -> None:
        """Reset accumulated LLM and embedding token counts."""
        ...


def normalize_llamaindex_model_name(model_name: str) -> str:
    """Translate the shared provider:model identifier to LlamaIndex model syntax."""
    provider, separator, model = model_name.partition(":")

    if not separator:
        return model_name

    if provider != "openai" or not model:
        raise ValueError("LlamaIndex OpenAI adapter requires an openai:model identifier")

    return model


def _create_llm(
    model_name: str,
    callback_manager: CallbackManager,
) -> _StructuredPredictLLM:
    """Create an OpenAI LlamaIndex LLM using the provider-supported sampling default."""
    return cast(
        _StructuredPredictLLM,
        OpenAI(
            model=normalize_llamaindex_model_name(model_name),
            temperature=LLAMAINDEX_PROVIDER_DEFAULT_TEMPERATURE,
            callback_manager=callback_manager,
        ),
    )


class LlamaIndexRuntime:
    """Execute structured vulnerability reasoning through LlamaIndex."""

    def __init__(self, model_name: str) -> None:
        """Create the LlamaIndex LLM and isolated usage callback state."""
        token_counter = TokenCountingHandler(verbose=False)
        callback_manager = CallbackManager([token_counter])

        self._token_counter = cast(_TokenCounter, token_counter)
        self._llm = _create_llm(
            model_name=model_name,
            callback_manager=callback_manager,
        )

    def consume_usage(self) -> LlamaIndexUsage:
        """Return accumulated usage and reset counters for the next benchmark run."""
        usage = LlamaIndexUsage(
            input_tokens=self._token_counter.prompt_llm_token_count,
            output_tokens=self._token_counter.completion_llm_token_count,
            total_tokens=self._token_counter.total_llm_token_count,
            model_calls=len(self._token_counter.llm_token_counts),
        )
        self._token_counter.reset_counts()
        return usage

    def run(self, system_prompt: str, user_prompt: str) -> LLMAnalysisDraft:
        """Execute one structured prediction using separate system and user messages."""
        prompt = ChatPromptTemplate(
            message_templates=[
                ChatMessage.from_str(
                    system_prompt,
                    role=MessageRole.SYSTEM,
                ),
                ChatMessage.from_str(
                    user_prompt,
                    role=MessageRole.USER,
                ),
            ]
        )
        output = self._llm.structured_predict(
            output_cls=LLMAnalysisDraft,
            prompt=prompt,
        )
        return LLMAnalysisDraft.model_validate(output)


class LlamaIndexVulnerabilityAnalyzer:
    """Produce structured vulnerability reasoning through a LlamaIndex runner."""

    def __init__(self, runner: LlamaIndexAnalysisRunner) -> None:
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
