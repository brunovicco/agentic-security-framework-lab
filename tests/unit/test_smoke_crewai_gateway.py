"""Provider-free tests for the CrewAI LiteLLM gateway smoke runner."""

import json
from pathlib import Path
from runpy import run_path
from typing import Any

import pytest
from pytest import MonkeyPatch

_SCRIPT_PATH = Path(__file__).parents[2] / "scripts" / "smoke_crewai_gateway.py"
_SCRIPT = run_path(str(_SCRIPT_PATH))
GatewayConfigSummary: Any = _SCRIPT["GatewayConfigSummary"]
GatewaySmokeRun: Any = _SCRIPT["GatewaySmokeRun"]
assess_gateway_smoke: Any = _SCRIPT["assess_gateway_smoke"]
configure_crewai_telemetry: Any = _SCRIPT["configure_crewai_telemetry"]
load_gateway_config_summary: Any = _SCRIPT["load_gateway_config_summary"]
run_gateway_smoke: Any = _SCRIPT["run_gateway_smoke"]
wait_for_gateway_readiness: Any = _SCRIPT["wait_for_gateway_readiness"]
write_smoke_artifacts: Any = _SCRIPT["write_smoke_artifacts"]


class _FakeResponse:
    def __init__(self, status: int) -> None:
        self.status = status


def _run(
    runtime: str,
    scenario_id: str,
    *,
    expected_match: bool = True,
    validation_passed: bool = True,
    analysis_source: str = "llm",
    analysis_attempts: int = 1,
    model_calls: int = 1,
    total_tokens: int = 120,
) -> Any:
    return GatewaySmokeRun(
        runtime=runtime,
        pattern=f"{runtime}-pattern",
        scenario_id=scenario_id,
        tags=("test",),
        model_alias="security-analysis",
        configured_upstream_model="openai/test-model",
        latency_ms=10.0,
        analysis_source=analysis_source,
        validation_passed=validation_passed,
        analysis_attempts=analysis_attempts,
        model_calls=model_calls,
        expected_match=expected_match,
        confidence=0.9,
        input_tokens=max(total_tokens - 20, 0),
        output_tokens=min(total_tokens, 20),
        total_tokens=total_tokens,
    )


def _passing_runs() -> tuple[Any, ...]:
    return tuple(
        _run(runtime, f"scenario-{index}")
        for runtime in ("agent_crew", "flow")
        for index in range(1, 6)
    )


def test_crewai_smoke_does_not_restore_direct_model_environment_contract() -> None:
    assert "AGENTIC_LAB_MODEL" not in _SCRIPT_PATH.read_text()


def test_configure_crewai_telemetry_disables_optional_tracing(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.delenv("CREWAI_TRACING_ENABLED", raising=False)

    configure_crewai_telemetry()

    assert _SCRIPT["os"].environ["CREWAI_TRACING_ENABLED"] == "false"


def test_wait_for_gateway_readiness_uses_official_endpoint(
    monkeypatch: MonkeyPatch,
) -> None:
    calls: list[Any] = []

    class FakeConnection:
        def __init__(self, host: str, port: int, timeout: float) -> None:
            calls.append(("connect", host, port, timeout))

        def request(self, method: str, path: str, headers: dict[str, str]) -> None:
            calls.append(("request", method, path, headers))

        def getresponse(self) -> _FakeResponse:
            return _FakeResponse(status=200)

        def close(self) -> None:
            calls.append(("close",))

    monkeypatch.setitem(
        wait_for_gateway_readiness.__globals__,
        "HTTPConnection",
        FakeConnection,
    )

    wait_for_gateway_readiness(
        "http://localhost:4000",
        "test-key",
        attempts=1,
        delay_seconds=0,
    )

    assert calls[1] == (
        "request",
        "GET",
        "/health/readiness",
        {"Authorization": "Bearer test-key"},
    )
    assert calls[-1] == ("close",)


def test_load_gateway_config_summary_reads_governed_alias(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        json.dumps(
            {
                "model_list": [
                    {
                        "model_name": "security-analysis",
                        "litellm_params": {"model": "openai/test-model"},
                    }
                ]
            }
        )
    )

    summary = load_gateway_config_summary(config_path)

    assert summary.model_alias == "security-analysis"
    assert summary.configured_upstream_model == "openai/test-model"


def test_run_gateway_smoke_rejects_noncanonical_scenario_count() -> None:
    config = GatewayConfigSummary(
        model_alias="security-analysis",
        configured_upstream_model="openai/test-model",
    )

    with pytest.raises(RuntimeError, match="expected 5 scenarios"):
        run_gateway_smoke((), config)


def test_gateway_smoke_assessment_requires_both_runtime_scenario_sets() -> None:
    runs = _passing_runs()[:-1]

    assessment = assess_gateway_smoke(runs)

    assert assessment.passed is False
    assert assessment.failures == (
        "unexpected_run_count",
        "flow:unexpected_run_count",
        "flow:unexpected_scenario_set",
    )


def test_gateway_smoke_assessment_fails_closed_on_runtime_evidence() -> None:
    runs = list(_passing_runs())
    runs[0] = _run("agent_crew", "scenario-1", expected_match=False)
    runs[1] = _run("agent_crew", "scenario-2", validation_passed=False)
    runs[2] = _run("agent_crew", "scenario-3", analysis_source="oracle_fallback")
    runs[3] = _run("agent_crew", "scenario-4", model_calls=0)
    runs[4] = _run(
        "agent_crew",
        "scenario-5",
        analysis_attempts=2,
        model_calls=1,
    )
    runs[5] = _run("flow", "scenario-1", total_tokens=0)

    assessment = assess_gateway_smoke(tuple(runs))

    assert assessment.passed is False
    assert assessment.failures == (
        "agent_crew:scenario-1:expected_mismatch",
        "agent_crew:scenario-2:validation_failure",
        "agent_crew:scenario-3:unexpected_analysis_source",
        "agent_crew:scenario-4:no_model_call",
        "agent_crew:scenario-4:incomplete_model_call_telemetry",
        "agent_crew:scenario-5:incomplete_model_call_telemetry",
        "flow:scenario-1:missing_usage_metadata",
    )


def test_gateway_smoke_artifact_is_non_baseline_and_secret_free(
    tmp_path: Path,
) -> None:
    config = GatewayConfigSummary(
        model_alias="security-analysis",
        configured_upstream_model="openai/test-model",
    )

    json_path, markdown_path = write_smoke_artifacts(
        config=config,
        runs=_passing_runs(),
        output_root=tmp_path,
    )

    payload = json.loads(json_path.read_text())
    markdown = markdown_path.read_text()

    assert payload["artifact_type"] == "gateway_smoke"
    assert payload["official_baseline"] is False
    assert payload["review_status"] == "pending_manual_trace_review"
    assert payload["framework"] == "crewai"
    assert payload["gateway_endpoint_persisted"] is False
    assert payload["model_alias"] == "security-analysis"
    assert payload["configured_upstream_evidence"] == "committed_litellm_config"
    assert payload["repetitions_per_scenario_per_runtime"] == 1
    assert payload["runtime_count"] == 2
    assert payload["scenario_count_per_runtime"] == 5
    assert payload["total_run_count"] == 10
    assert payload["smoke_assessment"]["passed"] is True
    assert "AGENTIC_LAB_GATEWAY_API_KEY" not in json_path.read_text()
    assert "http://localhost:4000" not in json_path.read_text()
    assert "Gateway endpoint and credentials are intentionally not persisted" in markdown
    assert "Official baseline: **no**" in markdown
