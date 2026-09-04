"""Regression tests for migrated framework gateway metadata contracts."""

from pathlib import Path
from runpy import run_path
from typing import Any

import pytest
from pytest import MonkeyPatch

_ROOT = Path(__file__).parents[2]
_CREWAI_SPECIFIC_RUNNERS = (
    _ROOT / "scripts" / "benchmark_crewai_scenarios.py",
    _ROOT / "scripts" / "benchmark_crewai_flow_scenarios.py",
    _ROOT / "scripts" / "smoke_crewai_gateway.py",
)
_BASELINE_SCRIPT: dict[str, Any] = run_path(
    str(_ROOT / "scripts" / "benchmark_adversarial_v2_workflow_baseline.py")
)
_SMOKE_SCRIPT: dict[str, Any] = run_path(
    str(_ROOT / "scripts" / "benchmark_adversarial_v2_workflow_smoke.py")
)


@pytest.mark.parametrize("path", _CREWAI_SPECIFIC_RUNNERS)
def test_crewai_specific_runners_do_not_require_direct_model_environment(path: Path) -> None:
    source = path.read_text()

    assert "AGENTIC_LAB_MODEL" not in source
    assert "gateway_model_alias" in source


def test_crewai_adapters_do_not_store_transitional_model_identity() -> None:
    analyzer_source = (
        _ROOT / "src" / "agentic_lab" / "adapters" / "crewai" / "analyzer.py"
    ).read_text()
    flow_source = (_ROOT / "src" / "agentic_lab" / "adapters" / "crewai" / "flow.py").read_text()

    assert "def __init__(self, model_name" not in analyzer_source
    assert "model_name:" not in flow_source
    assert "self._model_name" not in flow_source


@pytest.mark.parametrize("script", (_BASELINE_SCRIPT, _SMOKE_SCRIPT))
def test_generic_runners_use_gateway_alias_for_every_migrated_workflow(
    script: dict[str, Any],
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGENTIC_LAB_MODEL", "openai:must-not-control-runtime")

    workflow_model_name = script["workflow_model_name"]

    assert workflow_model_name("crewai-flow") == "security-analysis"
    assert workflow_model_name("llamaindex-workflow") == "security-analysis"
    assert workflow_model_name("agno-workflow") == "security-analysis"
    assert "require_direct_model_name" not in script
