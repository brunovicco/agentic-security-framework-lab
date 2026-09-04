"""Regression tests for the post-migration LlamaIndex gateway identity contract."""

import pytest

from agentic_lab.adapters.llamaindex.workflow import LlamaIndexWorkflowRuntime


def test_workflow_runtime_accepts_only_governed_gateway_alias() -> None:
    runtime = LlamaIndexWorkflowRuntime("security-analysis")

    assert runtime is not None


def test_workflow_runtime_rejects_direct_provider_model_identity() -> None:
    with pytest.raises(ValueError, match="governed gateway alias"):
        LlamaIndexWorkflowRuntime("openai:gpt-5.6-luna")
