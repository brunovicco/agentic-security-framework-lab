"""CrewAI LLM construction through the centralized LiteLLM gateway."""

from crewai import LLM

from agentic_lab.adapters.gateway import (
    gateway_api_key,
    gateway_base_url,
    gateway_model_alias,
)


def create_crewai_llm() -> LLM:
    """Create a CrewAI client for the governed OpenAI-compatible gateway alias."""
    return LLM(
        model=gateway_model_alias(),
        custom_openai=True,
        base_url=gateway_base_url(),
        api_key=gateway_api_key(),
    )
