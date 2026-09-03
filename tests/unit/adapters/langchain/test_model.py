"""Tests for LangChain chat-model construction."""

import pytest
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from agentic_lab.adapters.langchain.model import create_chat_model


def test_create_chat_model_requires_gateway_base_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fail explicitly when the LiteLLM gateway endpoint is missing."""
    monkeypatch.delenv("AGENTIC_LAB_GATEWAY_BASE_URL", raising=False)
    monkeypatch.setenv("AGENTIC_LAB_GATEWAY_API_KEY", "test-gateway-key")

    with pytest.raises(RuntimeError, match="AGENTIC_LAB_GATEWAY_BASE_URL"):
        create_chat_model()


def test_create_chat_model_requires_gateway_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fail explicitly when the LiteLLM gateway credential is missing."""
    monkeypatch.setenv("AGENTIC_LAB_GATEWAY_BASE_URL", "http://localhost:4000")
    monkeypatch.delenv("AGENTIC_LAB_GATEWAY_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="AGENTIC_LAB_GATEWAY_API_KEY"):
        create_chat_model()


def test_create_chat_model_uses_governed_gateway_alias(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Build an OpenAI-compatible client without accepting a direct provider model."""
    monkeypatch.setenv("AGENTIC_LAB_GATEWAY_BASE_URL", "http://localhost:4000")
    monkeypatch.setenv("AGENTIC_LAB_GATEWAY_API_KEY", "test-gateway-key")
    monkeypatch.setenv("AGENTIC_LAB_MODEL", "openai:should-not-be-used")

    model = create_chat_model()

    assert isinstance(model, ChatOpenAI)
    assert model.model_name == "security-analysis"
    assert model.openai_api_base == "http://localhost:4000"
    assert isinstance(model.openai_api_key, SecretStr)
    assert model.openai_api_key.get_secret_value() == "test-gateway-key"
    assert model.temperature == 0
    assert model.max_retries == 2
