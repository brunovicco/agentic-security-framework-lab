"""LangChain chat-model construction through the LiteLLM gateway."""

import os

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI

_GATEWAY_BASE_URL_ENV = "AGENTIC_LAB_GATEWAY_BASE_URL"
_GATEWAY_API_KEY_ENV = "AGENTIC_LAB_GATEWAY_API_KEY"
_GATEWAY_MODEL_ALIAS = "security-analysis"


def _required_environment_value(name: str) -> str:
    """Return a required non-blank environment value."""
    value = os.environ.get(name)
    if value is None or not value.strip():
        raise RuntimeError(f"{name} must be configured for LiteLLM gateway access")
    return value


def create_chat_model() -> BaseChatModel:
    """Create the LangChain client for the governed LiteLLM model alias."""
    return ChatOpenAI(
        model=_GATEWAY_MODEL_ALIAS,
        base_url=_required_environment_value(_GATEWAY_BASE_URL_ENV),
        api_key=_required_environment_value(_GATEWAY_API_KEY_ENV),
        temperature=0,
        max_retries=2,
    )
