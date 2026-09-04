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
def test_crewai_only_generic_runner_does_not_require_direct_model(
    script: dict[str, Any],
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.delenv("AGENTIC_LAB_MODEL", raising=False)

    direct_model = script["require_direct_model_name"](("crewai-flow",))
    crewai_model = script["workflow_model_name"]("crewai-flow", direct_model)

    assert direct_model is None
    assert crewai_model == "security-analysis"


@pytest.mark.parametrize("script", (_BASELINE_SCRIPT, _SMOKE_SCRIPT))
def test_generic_runner_retains_direct_model_contract_only_for_agno(
    script: dict[str, Any],
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.delenv("AGENTIC_LAB_MODEL", raising=False)

    with pytest.raises(RuntimeError, match="direct-provider model"):
        script["require_direct_model_name"](("agno-workflow",))

    monkeypatch.setenv("AGENTIC_LAB_MODEL", "openai:direct-test-model")
    direct_model = script["require_direct_model_name"](("llamaindex-workflow", "agno-workflow"))

    assert direct_model == "openai:direct-test-model"
    llamaindex_model = script["workflow_model_name"]("llamaindex-workflow", direct_model)
    assert llamaindex_model == "security-analysis"
    agno_model = script["workflow_model_name"]("agno-workflow", direct_model)
    assert agno_model == "openai:direct-test-model"
