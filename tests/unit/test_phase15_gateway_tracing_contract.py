"""Regression tests for Phase 15 gateway identity and vendor telemetry guards."""

from pathlib import Path

_REPO_ROOT = Path(__file__).parents[2]
_SCRIPTS = _REPO_ROOT / "scripts"
_SRC = _REPO_ROOT / "src" / "agentic_lab" / "adapters" / "crewai"


def test_llamaindex_benchmark_uses_governed_gateway_alias() -> None:
    """Prevent the final benchmark from restoring legacy direct-model selection."""
    source = (_SCRIPTS / "benchmark_llamaindex_workflow_scenarios.py").read_text()

    assert "AGENTIC_LAB_MODEL" not in source
    assert "from agentic_lab.adapters.gateway import gateway_model_alias" in source
    assert "return gateway_model_alias()" in source


def test_final_evaluation_disables_framework_owned_telemetry() -> None:
    """Keep rich vendor telemetry opt-out without disabling project-owned OTel."""
    source = (_SCRIPTS / "run_final_evaluation.py").read_text()

    assert 'environment.pop("AGENTIC_LAB_MODEL", None)' in source
    assert 'environment["CREWAI_TRACING_ENABLED"] = "false"' in source
    assert 'environment["CREWAI_DISABLE_TELEMETRY"] = "true"' in source
    assert 'environment["CREWAI_DISABLE_TRACKING"] = "true"' in source
    assert 'environment["CREWAI_TESTING"] = "true"' in source
    assert 'environment["AGNO_TELEMETRY"] = "false"' in source
    assert "OTEL_SDK_DISABLED" not in source


def test_crewai_adapters_explicitly_disable_proprietary_tracing() -> None:
    """Require public CrewAI per-execution tracing overrides at both adapter paths."""
    analyzer_source = (_SRC / "analyzer.py").read_text()
    flow_source = (_SRC / "flow.py").read_text()

    assert "tracing=False" in analyzer_source
    assert "tracing=False" in flow_source
