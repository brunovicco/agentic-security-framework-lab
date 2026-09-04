"""LlamaIndex structured vulnerability-analysis adapter."""

from dataclasses import dataclass
from typing import Any, Protocol, cast

from llama_index.core.base.llms.types import ChatMessage, MessageRole
from llama_index.core.callbacks import CallbackManager, TokenCountingHandler
from llama_index.core.prompts import ChatPromptTemplate
from llama_index.llms.openai_like import OpenAILike
from pydantic import BaseModel

from agentic_lab.adapters.gateway import (
    gateway_api_key,
    gateway_base_url,
    gateway_model_alias,
)
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


class _GatewayOpenAILike(OpenAILike):
    """Use LlamaIndex OpenAI compatibility without imposing provider sampling settings."""

    def _get_model_kwargs(self, **kwargs: Any) -> dict[str, Any]:
        """Remove OpenAILike's default temperature before sending a gateway request."""
        model_kwargs = super()._get_model_kwargs(**kwargs)
        model_kwargs.pop("temperature", None)
        return model_kwargs


def _create_llm(
    _model_name: str,
    callback_manager: CallbackManager,
) -> _StructuredPredictLLM:
    """Create a structured LlamaIndex client through the governed gateway alias."""
    return cast(
        _StructuredPredictLLM,
        _GatewayOpenAILike(
            model=gateway_model_alias(),
            api_base=gateway_base_url(),
            api_key=gateway_api_key(),
            is_chat_model=True,
            is_function_calling_model=True,
            callback_manager=callback_manager,
        ),
    )


class LlamaIndexRuntime:
    """Execute structured vulnerability reasoning through LlamaIndex."""

    def __init__(
        self,
        model_name: str,
        token_counter: TokenCountingHandler | None = None,
    ) -> None:
        """Create gateway-backed LlamaIndex LLM while retaining transitional metadata input."""
        handler = token_counter or TokenCountingHandler(verbose=False)
        callback_manager = CallbackManager([handler])

        self._token_counter = cast(_TokenCounter, handler)
        self._llm = _create_llm(
            model_name,
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
        documents: tuple[EvidenceDocument, ...] = (),
    ) -> LLMAnalysisDraft:
        """Analyze vulnerability evidence against asset inventory and documents."""
        return self._runner.run(
            system_prompt=SECURITY_ANALYSIS_SYSTEM_PROMPT,
            user_prompt=build_security_analysis_user_prompt(
                vulnerability=vulnerability,
                assets=assets,
                feedback=feedback,
                documents=documents,
            ),
        )
