"""CrewAI LLM construction through the centralized LiteLLM gateway."""

from typing import Protocol, cast

from crewai import LLM

from agentic_lab.adapters.gateway import (
    gateway_api_key,
    gateway_base_url,
    gateway_model_alias,
)


class _OpenAICompatibleLLMFactory(Protocol):
    """Type the CrewAI factory kwargs supported by its runtime `__new__` path."""

    def __call__(
        self,
        *,
        model: str,
        custom_openai: bool,
        base_url: str,
        api_key: str,
    ) -> LLM:
        """Construct one native OpenAI-compatible CrewAI client."""
        ...


def _openai_compatible_llm_factory() -> _OpenAICompatibleLLMFactory:
    """Narrow CrewAI's partially typed LLM factory to its supported gateway surface."""
    return cast(_OpenAICompatibleLLMFactory, LLM)


def create_crewai_llm() -> LLM:
    """Create a CrewAI client for the governed OpenAI-compatible gateway alias."""
    return _openai_compatible_llm_factory()(
        model=gateway_model_alias(),
        custom_openai=True,
        base_url=gateway_base_url(),
        api_key=gateway_api_key(),
    )
