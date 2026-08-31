"""Tests for LangChain chat-model construction."""

import pytest

from agentic_lab.adapters.langchain.model import create_chat_model


def test_create_chat_model_requires_configured_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fail explicitly when no lab chat model is configured."""
    monkeypatch.delenv("AGENTIC_LAB_MODEL", raising=False)

    with pytest.raises(RuntimeError, match="AGENTIC_LAB_MODEL"):
        create_chat_model()
