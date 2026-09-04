"""LangChain chat-model construction through the LiteLLM gateway."""

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from agentic_lab.adapters.gateway import (
    gateway_api_key,
    gateway_base_url,
    gateway_model_alias,
)


def create_chat_model() -> BaseChatModel:
    """Create the LangChain client for the governed LiteLLM model alias."""
    return ChatOpenAI(
        model=gateway_model_alias(),
        base_url=gateway_base_url(),
        api_key=SecretStr(gateway_api_key()),
        max_retries=2,
    )
