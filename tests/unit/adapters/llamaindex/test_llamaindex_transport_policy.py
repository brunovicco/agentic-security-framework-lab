"""Contract tests for the LlamaIndex gateway transport policy."""

from llama_index.core.callbacks import CallbackManager
from pytest import MonkeyPatch

from agentic_lab.adapters.llamaindex import analyzer as llamaindex_module
from agentic_lab.adapters.llamaindex.analyzer import (
    LLAMAINDEX_GATEWAY_MAX_RETRIES,
    LLAMAINDEX_GATEWAY_REQUEST_TIMEOUT_SECONDS,
    LlamaIndexRuntime,
)


def test_runtime_disables_client_retries_and_bounds_gateway_request(
    monkeypatch: MonkeyPatch,
) -> None:
    """Keep transport retries explicit and below the Workflow orchestration deadline."""
    captured_kwargs: dict[str, object] = {}

    class StubGatewayLLM:
        def __init__(self, **kwargs: object) -> None:
            captured_kwargs.update(kwargs)

    monkeypatch.setenv("AGENTIC_LAB_GATEWAY_BASE_URL", "http://gateway.test:4000")
    monkeypatch.setenv("AGENTIC_LAB_GATEWAY_API_KEY", "gateway-test-key")
    monkeypatch.setattr(llamaindex_module, "LlamaIndexGatewayLLM", StubGatewayLLM)

    LlamaIndexRuntime()

    assert captured_kwargs["model"] == "security-analysis"
    assert captured_kwargs["api_base"] == "http://gateway.test:4000"
    assert captured_kwargs["api_key"] == "gateway-test-key"
    assert captured_kwargs["max_retries"] == LLAMAINDEX_GATEWAY_MAX_RETRIES == 0
    assert captured_kwargs["timeout"] == LLAMAINDEX_GATEWAY_REQUEST_TIMEOUT_SECONDS == 30.0
    assert isinstance(captured_kwargs["callback_manager"], CallbackManager)
