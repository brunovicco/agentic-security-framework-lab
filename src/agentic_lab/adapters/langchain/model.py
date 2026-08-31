"""LangChain chat-model construction."""

import os

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel

_MODEL_ENV = "AGENTIC_LAB_MODEL"


def create_chat_model() -> BaseChatModel:
    """Create the configured LangChain chat model."""
    model_name = os.environ.get(_MODEL_ENV)

    if not model_name:
        raise RuntimeError(f"{_MODEL_ENV} must identify the chat model used by the lab")

    return init_chat_model(
        model_name,
        temperature=0,
        max_retries=2,
    )
