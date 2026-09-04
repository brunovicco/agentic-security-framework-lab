"""Provider-free tests for the LangGraph LiteLLM gateway smoke runner."""

import json
from pathlib import Path
from runpy import run_path
from typing import Any

import pytest
from pytest import MonkeyPatch

_SCRIPT = run_path(str(Path(__file__).parents[2] / "scripts" / "smoke_langgraph_gateway.py"))
GatewayConfigSummary: Any = _SCRIPT["GatewayConfigSummary"]
GatewaySmokeRun: Any = _SCRIPT["GatewaySmokeRun"]
assess_gateway_smoke: Any = _SCRIPT["assess_gateway_smoke"]
load_gateway_config_summary: Any = _SCRIPT["load_gateway_config_summary"]
require_gateway_environment: Any = _SCRIPT["require_gateway_environment"]
wait_for_gateway_readiness: Any = _SCRIPT["wait_for_gateway_readiness"]
write_smoke_artifacts: Any = _SCRIPT["write_smoke_artifacts"]


class _FakeResponse:
    def __init__(self, status: int) -> None:
        self.status = status


def _run(
    scenario_id: str,
    *,
    expected_match: bool = True,
    validation_passed: bool = True,
    model_calls: int = 1,
    total_tokens: int = 120,
) -> Any:
    return GatewaySmokeRun(
        scenario_id=scenario_id,
        tags=("test",),
        model_alias="security-analysis",
        configured_upstream_model="openai/test-model",
        latency_ms=10.0,
        analysis_source="llm",
        validation_passed=validation_passed,
        analysis_attempts=model_calls,
        model_calls=model_calls,
        expected_match=expected_match,
        confidence=0.9,
        input_tokens=max(total_tokens - 20, 0),
        output_tokens=min(total_tokens, 20),
        total_tokens=total_tokens,
    )


def _passing_runs() -> tuple[Any, ...]:
    return tuple(_run(f"scenario-{index}") for index in range(1, 6))


def test_require_gateway_environment_requires_both_values(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.delenv("AGENTIC_LAB_GATEWAY_BASE_URL", raising=False)
    monkeypatch.setenv("AGENTIC_LAB_GATEWAY_API_KEY", "test-key")

    with pytest.raises(RuntimeError, match="AGENTIC_LAB_GATEWAY_BASE_URL"):
        require_gateway_environment()

    monkeypatch.setenv("AGENTIC_LAB_GATEWAY_BASE_URL", "http://localhost:4000")
    monkeypatch.delenv("AGENTIC_LAB_GATEWAY_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="AGENTIC_LAB_GATEWAY_API_KEY"):
        require_gateway_environment()


def test_require_gateway_environment_returns_configured_values(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGENTIC_LAB_GATEWAY_BASE_URL", "http://localhost:4000")
    monkeypatch.setenv("AGENTIC_LAB_GATEWAY_API_KEY", "test-key")

    assert require_gateway_environment() == (
        "http://localhost:4000",
        "test-key",
    )


def test_wait_for_gateway_readiness_uses_official_readiness_endpoint(
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

    assert calls[0] == ("connect", "localhost", 4000, 2.0)
    assert calls[1] == (
        "request",
        "GET",
        "/health/readiness",
        {"Authorization": "Bearer test-key"},
    )
    assert calls[-1] == ("close",)


def test_wait_for_gateway_readiness_rejects_non_http_scheme() -> None:
    with pytest.raises(RuntimeError, match="must use http or https"):
        wait_for_gateway_readiness(
            "file:///tmp/litellm.sock",
            "test-key",
            attempts=1,
            delay_seconds=0,
        )


def test_wait_for_gateway_readiness_retries_connection_refusal(
    monkeypatch: MonkeyPatch,
) -> None:
    attempts_seen = 0

    class FakeConnection:
        def __init__(self, host: str, port: int, timeout: float) -> None:
            return None

        def request(self, method: str, path: str, headers: dict[str, str]) -> None:
            nonlocal attempts_seen
            attempts_seen += 1
            if attempts_seen < 3:
                raise ConnectionRefusedError("connection refused")

        def getresponse(self) -> _FakeResponse:
            return _FakeResponse(status=200)

        def close(self) -> None:
            return None

    monkeypatch.setitem(
        wait_for_gateway_readiness.__globals__,
        "HTTPConnection",
        FakeConnection,
    )

    wait_for_gateway_readiness(
        "http://localhost:4000",
        "test-key",
        attempts=3,
        delay_seconds=0,
    )

    assert attempts_seen == 3


def test_wait_for_gateway_readiness_fails_with_startup_diagnostic(
    monkeypatch: MonkeyPatch,
) -> None:
    class FakeConnection:
        def __init__(self, host: str, port: int, timeout: float) -> None:
            return None

        def request(self, method: str, path: str, headers: dict[str, str]) -> None:
            raise ConnectionRefusedError("connection refused")

        def getresponse(self) -> _FakeResponse:
            return _FakeResponse(status=503)

        def close(self) -> None:
            return None

    monkeypatch.setitem(
        wait_for_gateway_readiness.__globals__,
        "HTTPConnection",
        FakeConnection,
    )

    with pytest.raises(RuntimeError, match="proxy process is still running"):
        wait_for_gateway_readiness(
            "http://localhost:4000",
            "test-key",
            attempts=2,
            delay_seconds=0,
        )


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


def test_load_gateway_config_summary_rejects_missing_alias(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(json.dumps({"model_list": []}))

    with pytest.raises(RuntimeError, match="exactly once"):
        load_gateway_config_summary(config_path)


def test_gateway_smoke_assessment_fails_closed() -> None:
    runs = list(_passing_runs())
    runs[0] = _run("scenario-1", expected_match=False)
    runs[1] = _run("scenario-2", validation_passed=False)
    runs[2] = _run("scenario-3", model_calls=0)
    runs[3] = _run("scenario-4", total_tokens=0)

    assessment = assess_gateway_smoke(tuple(runs))

    assert assessment.passed is False
    assert assessment.failures == (
        "scenario-1:expected_mismatch",
        "scenario-2:validation_failure",
        "scenario-3:no_model_call",
        "scenario-4:missing_usage_metadata",
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
    assert payload["gateway_endpoint_persisted"] is False
    assert payload["model_alias"] == "security-analysis"
    assert payload["configured_upstream_evidence"] == "committed_litellm_config"
    assert payload["repetitions_per_scenario"] == 1
    assert payload["scenario_count"] == 5
    assert payload["smoke_assessment"]["passed"] is True
    assert "Gateway endpoint and credentials are intentionally not persisted" in markdown
    assert "Official baseline: **no**" in markdown
