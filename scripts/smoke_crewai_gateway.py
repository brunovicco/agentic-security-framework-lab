"""Run a non-baseline CrewAI compatibility smoke through the LiteLLM gateway."""

import json
import os
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from http.client import HTTPConnection, HTTPSConnection
from pathlib import Path
from time import perf_counter, sleep
from typing import Literal
from urllib.parse import urlsplit

from agentic_lab.adapters.crewai.analyzer import (
    CrewAIRuntime,
    CrewAIUsage,
    CrewAIVulnerabilityAnalyzer,
)
from agentic_lab.adapters.crewai.flow import CrewAIFlowRuntime
from agentic_lab.adapters.fixtures.evaluation import load_evaluation_scenarios
from agentic_lab.adapters.gateway import (
    gateway_api_key,
    gateway_base_url,
    gateway_model_alias,
)
from agentic_lab.application.contracts import AssetAssessment
from agentic_lab.application.evaluation import EvaluationScenario
from agentic_lab.application.evidence import AnalysisEvidenceBundle
from agentic_lab.application.validated_analysis import (
    ValidatedAnalysisOutput,
    run_validated_analysis,
)

_GATEWAY_CONFIG_PATH = Path("config/litellm/config.yaml")
_OUTPUT_ROOT = Path("artifacts/gateway-smoke/crewai")
_EXPECTED_SCENARIO_COUNT = 5
_READINESS_PATH = "health/readiness"
_READINESS_ATTEMPTS = 20
_READINESS_DELAY_SECONDS = 1.0
_READINESS_REQUEST_TIMEOUT_SECONDS = 2.0

RuntimeKey = Literal["agent_crew", "flow"]
_RUNTIME_PATTERNS: dict[RuntimeKey, str] = {
    "agent_crew": "single_agent_external_evaluator_optimizer_via_litellm_proxy",
    "flow": "flow_direct_llm_evaluator_optimizer_via_litellm_proxy",
}


@dataclass(frozen=True, slots=True)
class GatewayConfigSummary:
    """Describe the committed gateway mapping without exposing credentials."""

    model_alias: str
    configured_upstream_model: str


@dataclass(frozen=True, slots=True)
class GatewaySmokeRun:
    """Capture one canonical scenario executed by one CrewAI runtime through the gateway."""

    runtime: RuntimeKey
    pattern: str
    scenario_id: str
    tags: tuple[str, ...]
    model_alias: str
    configured_upstream_model: str
    latency_ms: float
    analysis_source: str
    validation_passed: bool
    analysis_attempts: int
    model_calls: int
    expected_match: bool
    confidence: float
    input_tokens: int
    output_tokens: int
    total_tokens: int


@dataclass(frozen=True, slots=True)
class SmokeAssessment:
    """Fail closed when either CrewAI runtime does not preserve required behavior."""

    passed: bool
    runs: int
    failures: tuple[str, ...]


def wait_for_gateway_readiness(
    base_url: str,
    api_key: str,
    *,
    attempts: int = _READINESS_ATTEMPTS,
    delay_seconds: float = _READINESS_DELAY_SECONDS,
) -> None:
    """Wait until the LiteLLM readiness endpoint accepts requests."""
    if attempts < 1:
        raise ValueError("Gateway readiness attempts must be at least 1")
    if delay_seconds < 0:
        raise ValueError("Gateway readiness delay must not be negative")

    parsed = urlsplit(base_url)
    if parsed.scheme not in {"http", "https"}:
        raise RuntimeError("Gateway base URL must use http or https")
    if parsed.hostname is None:
        raise RuntimeError("Gateway base URL must include a hostname")

    port = parsed.port
    if port is None:
        port = 443 if parsed.scheme == "https" else 80

    base_path = parsed.path.rstrip("/")
    readiness_path = f"{base_path}/{_READINESS_PATH}" if base_path else f"/{_READINESS_PATH}"
    connection_type = HTTPSConnection if parsed.scheme == "https" else HTTPConnection
    headers = {"Authorization": f"Bearer {api_key}"}
    last_error = "no response"

    for attempt in range(1, attempts + 1):
        connection = connection_type(
            parsed.hostname,
            port,
            timeout=_READINESS_REQUEST_TIMEOUT_SECONDS,
        )
        try:
            connection.request("GET", readiness_path, headers=headers)
            response = connection.getresponse()
            if response.status == 200:
                return
            last_error = f"HTTP {response.status}"
        except OSError as exc:
            last_error = f"{type(exc).__name__}: {exc}"
        finally:
            connection.close()

        if attempt < attempts:
            sleep(delay_seconds)

    raise RuntimeError(
        "LiteLLM gateway did not become ready before the CrewAI smoke started. "
        f"Last readiness error: {last_error}. "
        "Verify that the proxy process is still running and inspect its startup logs."
    )


def load_gateway_config_summary(
    path: Path = _GATEWAY_CONFIG_PATH,
) -> GatewayConfigSummary:
    """Read the committed alias-to-upstream mapping used by the smoke."""
    payload = json.loads(path.read_text())
    model_list = payload.get("model_list")
    if not isinstance(model_list, list):
        raise RuntimeError("LiteLLM gateway config must define model_list")

    alias = gateway_model_alias()
    matches = [
        entry
        for entry in model_list
        if isinstance(entry, dict) and entry.get("model_name") == alias
    ]
    if len(matches) != 1:
        raise RuntimeError(f"LiteLLM gateway config must define alias {alias!r} exactly once")

    params = matches[0].get("litellm_params")
    if not isinstance(params, dict):
        raise RuntimeError(f"LiteLLM alias {alias!r} must define litellm_params")

    upstream = params.get("model")
    if not isinstance(upstream, str) or not upstream.strip():
        raise RuntimeError(f"LiteLLM alias {alias!r} must define a non-blank upstream model")

    return GatewayConfigSummary(
        model_alias=alias,
        configured_upstream_model=upstream,
    )


def configure_crewai_telemetry() -> None:
    """Disable optional CrewAI tracing for the controlled headless smoke."""
    os.environ["CREWAI_TRACING_ENABLED"] = "false"


def build_evidence_bundle(scenario: EvaluationScenario) -> AnalysisEvidenceBundle:
    """Convert one canonical evaluation scenario into executable evidence."""
    return {
        "vulnerability": scenario.vulnerability,
        "assets": scenario.assets,
        "policy": scenario.policy,
    }


def matches_expected(
    scenario: EvaluationScenario,
    observed_assets: tuple[AssetAssessment, ...],
) -> bool:
    """Compare final asset applicability with framework-neutral expected truth."""
    expected = {item.asset_id: item.status for item in scenario.expected_assets}
    observed = {item.asset_id: item.status for item in observed_assets}
    return observed == expected


def _build_run(
    *,
    runtime: RuntimeKey,
    scenario: EvaluationScenario,
    config: GatewayConfigSummary,
    output: ValidatedAnalysisOutput,
    usage: CrewAIUsage,
    latency_ms: float,
) -> GatewaySmokeRun:
    """Normalize one CrewAI runtime execution into smoke evidence."""
    return GatewaySmokeRun(
        runtime=runtime,
        pattern=_RUNTIME_PATTERNS[runtime],
        scenario_id=scenario.scenario_id,
        tags=scenario.tags,
        model_alias=config.model_alias,
        configured_upstream_model=config.configured_upstream_model,
        latency_ms=round(latency_ms, 2),
        analysis_source=output.analysis_source,
        validation_passed=output.validation_passed,
        analysis_attempts=output.analysis_attempts,
        model_calls=usage.model_calls,
        expected_match=matches_expected(scenario, output.result.assets),
        confidence=output.result.confidence,
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        total_tokens=usage.total_tokens,
    )


def run_agent_crew_smoke(
    scenarios: tuple[EvaluationScenario, ...],
    config: GatewayConfigSummary,
) -> tuple[GatewaySmokeRun, ...]:
    """Run canonical scenarios through CrewAI Agent/Task/Crew and the gateway."""
    runtime = CrewAIRuntime(config.model_alias)
    analyzer = CrewAIVulnerabilityAnalyzer(runtime)
    runs: list[GatewaySmokeRun] = []

    for scenario in scenarios:
        stale_usage = runtime.consume_usage()
        if stale_usage.total_tokens or stale_usage.model_calls:
            raise RuntimeError("CrewAI Agent/Crew usage telemetry was not clean before smoke run")

        started_at = perf_counter()
        output = run_validated_analysis(
            analyzer=analyzer,
            evidence_bundle=build_evidence_bundle(scenario),
        )
        latency_ms = (perf_counter() - started_at) * 1000
        usage = runtime.consume_usage()
        run = _build_run(
            runtime="agent_crew",
            scenario=scenario,
            config=config,
            output=output,
            usage=usage,
            latency_ms=latency_ms,
        )
        runs.append(run)
        print(json.dumps({"type": "gateway_smoke_run", **asdict(run)}))

    return tuple(runs)


def run_flow_smoke(
    scenarios: tuple[EvaluationScenario, ...],
    config: GatewayConfigSummary,
) -> tuple[GatewaySmokeRun, ...]:
    """Run canonical scenarios through CrewAI Flow and the gateway."""
    runtime = CrewAIFlowRuntime(config.model_alias)
    runs: list[GatewaySmokeRun] = []

    for scenario in scenarios:
        started_at = perf_counter()
        execution = runtime.run(build_evidence_bundle(scenario))
        latency_ms = (perf_counter() - started_at) * 1000
        run = _build_run(
            runtime="flow",
            scenario=scenario,
            config=config,
            output=execution.output,
            usage=execution.usage,
            latency_ms=latency_ms,
        )
        runs.append(run)
        print(json.dumps({"type": "gateway_smoke_run", **asdict(run)}))

    return tuple(runs)


def run_gateway_smoke(
    scenarios: tuple[EvaluationScenario, ...],
    config: GatewayConfigSummary,
) -> tuple[GatewaySmokeRun, ...]:
    """Run each canonical scenario exactly once through both CrewAI runtime patterns."""
    if len(scenarios) != _EXPECTED_SCENARIO_COUNT:
        raise RuntimeError(f"CrewAI gateway smoke expected {_EXPECTED_SCENARIO_COUNT} scenarios")

    return (
        *run_agent_crew_smoke(scenarios, config),
        *run_flow_smoke(scenarios, config),
    )


def assess_gateway_smoke(runs: tuple[GatewaySmokeRun, ...]) -> SmokeAssessment:
    """Require correct final behavior plus observable provider usage for every run."""
    failures: list[str] = []
    expected_total_runs = _EXPECTED_SCENARIO_COUNT * len(_RUNTIME_PATTERNS)

    if len(runs) != expected_total_runs:
        failures.append("unexpected_run_count")

    for runtime in _RUNTIME_PATTERNS:
        runtime_runs = tuple(run for run in runs if run.runtime == runtime)
        if len(runtime_runs) != _EXPECTED_SCENARIO_COUNT:
            failures.append(f"{runtime}:unexpected_run_count")
        if len({run.scenario_id for run in runtime_runs}) != _EXPECTED_SCENARIO_COUNT:
            failures.append(f"{runtime}:unexpected_scenario_set")

    for run in runs:
        prefix = f"{run.runtime}:{run.scenario_id}"
        if not run.expected_match:
            failures.append(f"{prefix}:expected_mismatch")
        if not run.validation_passed:
            failures.append(f"{prefix}:validation_failure")
        if run.analysis_source != "llm":
            failures.append(f"{prefix}:unexpected_analysis_source")
        if run.analysis_attempts < 1:
            failures.append(f"{prefix}:no_analysis_attempt")
        if run.model_calls < 1:
            failures.append(f"{prefix}:no_model_call")
        if run.model_calls < run.analysis_attempts:
            failures.append(f"{prefix}:incomplete_model_call_telemetry")
        if run.total_tokens < 1:
            failures.append(f"{prefix}:missing_usage_metadata")

    return SmokeAssessment(
        passed=not failures,
        runs=len(runs),
        failures=tuple(failures),
    )


def render_markdown(
    generated_at: str,
    config: GatewayConfigSummary,
    runs: tuple[GatewaySmokeRun, ...],
    assessment: SmokeAssessment,
) -> str:
    """Render the human-readable non-baseline CrewAI gateway smoke report."""
    lines = [
        "# CrewAI LiteLLM Gateway Smoke",
        "",
        f"Generated: `{generated_at}`",
        "",
        "Artifact type: `gateway_smoke`",
        "",
        "Official baseline: **no**",
        "",
        "Review status: `pending_manual_trace_review`",
        "",
        f"Client model alias: `{config.model_alias}`",
        "",
        f"Configured upstream model: `{config.configured_upstream_model}`",
        "",
        (
            "The upstream value above comes from the committed LiteLLM configuration; "
            "it is configuration evidence, not independent provider-response attestation."
        ),
        "",
        "Gateway endpoint and credentials are intentionally not persisted in this artifact.",
        "",
        f"Smoke assessment: **{'PASS' if assessment.passed else 'FAIL'}**",
        "",
        (
            "| Runtime | Scenario | Expected match | Validation | Attempts | Calls | Tokens | "
            "Latency ms | Source |"
        ),
        "|---|---|---:|---:|---:|---:|---:|---:|---|",
    ]

    for run in runs:
        lines.append(
            "| "
            f"{run.runtime} | "
            f"{run.scenario_id} | "
            f"{'yes' if run.expected_match else 'no'} | "
            f"{'pass' if run.validation_passed else 'fail'} | "
            f"{run.analysis_attempts} | "
            f"{run.model_calls} | "
            f"{run.total_tokens} | "
            f"{run.latency_ms:.2f} | "
            f"{run.analysis_source} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            (
                "This smoke verifies two distinct CrewAI integration surfaces: the "
                "Agent/Task/Crew path with application-owned evaluation and the direct "
                "LLM path inside CrewAI Flow. Both must preserve expected truth and "
                "deterministic validation while exercising the governed LiteLLM alias."
            ),
            "",
            (
                "Agent/Crew usage is accumulated across separate Crew kickoffs when the "
                "application evaluator retries. Flow usage comes from `flow.usage_metrics`, "
                "which aggregates LLM calls inside one Flow kickoff."
            ),
            "",
            (
                "The smoke performs one execution per canonical scenario per runtime. "
                "It is compatibility evidence and must not be used as a performance "
                "baseline or framework ranking."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def write_smoke_artifacts(
    config: GatewayConfigSummary,
    runs: tuple[GatewaySmokeRun, ...],
    output_root: Path = _OUTPUT_ROOT,
) -> tuple[Path, Path]:
    """Persist CrewAI gateway smoke evidence outside official benchmark namespaces."""
    generated_at = datetime.now(UTC).isoformat()
    assessment = assess_gateway_smoke(runs)
    output_root.mkdir(parents=True, exist_ok=True)

    payload = {
        "schema_version": "1",
        "artifact_type": "gateway_smoke",
        "official_baseline": False,
        "review_status": "pending_manual_trace_review",
        "generated_at_utc": generated_at,
        "framework": "crewai",
        "patterns": dict(_RUNTIME_PATTERNS),
        "gateway_transport": "openai_compatible",
        "gateway_endpoint_persisted": False,
        "model_alias": config.model_alias,
        "configured_upstream_model": config.configured_upstream_model,
        "configured_upstream_evidence": "committed_litellm_config",
        "repetitions_per_scenario_per_runtime": 1,
        "runtime_count": len(_RUNTIME_PATTERNS),
        "scenario_count_per_runtime": _EXPECTED_SCENARIO_COUNT,
        "total_run_count": len(runs),
        "runs": [asdict(run) for run in runs],
        "smoke_assessment": asdict(assessment),
    }

    json_path = output_root / "latest.json"
    markdown_path = output_root / "latest.md"
    json_path.write_text(json.dumps(payload, indent=2) + "\n")
    markdown_path.write_text(render_markdown(generated_at, config, runs, assessment))
    return json_path, markdown_path


def main() -> None:
    """Execute the provider-backed CrewAI gateway smoke and persist reviewable evidence."""
    base_url = gateway_base_url()
    api_key = gateway_api_key()
    wait_for_gateway_readiness(base_url, api_key)
    configure_crewai_telemetry()
    config = load_gateway_config_summary()
    scenarios = load_evaluation_scenarios()
    runs = run_gateway_smoke(scenarios=scenarios, config=config)
    assessment = assess_gateway_smoke(runs)
    json_path, markdown_path = write_smoke_artifacts(config=config, runs=runs)

    print(json.dumps({"type": "gateway_smoke_assessment", **asdict(assessment)}))
    print(f"artifact_json: {json_path}")
    print(f"artifact_markdown: {markdown_path}")

    if not assessment.passed:
        raise RuntimeError("CrewAI LiteLLM gateway smoke failed")


if __name__ == "__main__":
    main()
