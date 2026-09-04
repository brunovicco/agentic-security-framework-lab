"""Regression tests for migrated LangGraph benchmark model metadata."""

from pathlib import Path

_SCRIPTS_DIR = Path(__file__).parents[2] / "scripts"


def test_langgraph_benchmarks_use_governed_gateway_alias() -> None:
    """Prevent migrated LangGraph runners from reintroducing direct-model selection."""
    runners = tuple(sorted(_SCRIPTS_DIR.glob("benchmark_langgraph*.py")))

    assert runners

    for runner in runners:
        source = runner.read_text()
        assert "AGENTIC_LAB_MODEL" not in source, runner.name
        assert "gateway_model_alias" in source, runner.name
        assert "model_name = gateway_model_alias()" in source, runner.name
