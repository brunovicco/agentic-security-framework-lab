"""Tests for CrewAI LLM construction through the centralized gateway."""

import pytest

from agentic_lab.adapters.crewai.model import create_crewai_llm


def test_create_crewai_llm_requires_gateway_base_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("AGENTIC_LAB_GATEWAY_BASE_URL", raising=False)
    monkeypatch.setenv("AGENTIC_LAB_GATEWAY_API_KEY", "test-gateway-key")

    with pytest.raises(RuntimeError, match="AGENTIC_LAB_GATEWAY_BASE_URL"):
        create_crewai_llm()


def test_create_crewai_llm_requires_gateway_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGENTIC_LAB_GATEWAY_BASE_URL", "http://localhost:4000")
    monkeypatch.delenv("AGENTIC_LAB_GATEWAY_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="AGENTIC_LAB_GATEWAY_API_KEY"):
        create_crewai_llm()


def test_create_crewai_llm_uses_governed_openai_compatible_gateway(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_kwargs: dict[str, object] = {}

    class StubLLM:
        def __init__(self, **kwargs: object) -> None:
            captured_kwargs.update(kwargs)

    monkeypatch.setenv("AGENTIC_LAB_GATEWAY_BASE_URL", "http://localhost:4000")
    monkeypatch.setenv("AGENTIC_LAB_GATEWAY_API_KEY", "test-gateway-key")
    monkeypatch.setenv("AGENTIC_LAB_MODEL", "openai:should-not-be-used")
    monkeypatch.setattr("agentic_lab.adapters.crewai.model.LLM", StubLLM)

    create_crewai_llm()

    assert captured_kwargs == {
        "model": "security-analysis",
        "custom_openai": True,
        "base_url": "http://localhost:4000",
        "api_key": "test-gateway-key",
    }
    assert "temperature" not in captured_kwargs
