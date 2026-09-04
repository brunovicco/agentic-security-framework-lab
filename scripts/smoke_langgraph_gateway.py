"""Run a non-baseline LangGraph compatibility smoke through the LiteLLM gateway."""

import json
import os
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter, sleep
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from langchain_core.callbacks import get_usage_metadata_callback
from langchain_core.messages import UsageMetadata

from agentic_lab.adapters.fixtures.evaluation import load_evaluation_scenarios
from agentic_lab.adapters.langchain.analyzer import LangChainVulnerabilityAnalyzer
from agentic_lab.adapters.langchain.model import create_chat_model, gateway_model_alias
from agentic_lab.adapters.langgraph.llm_graph import run_llm_analysis_graph_with_evidence
from agentic_lab.application.contracts import AssetAssessment
from agentic_lab.application.evaluation import EvaluationScenario
from agentic_lab.application.evidence import AnalysisEvidenceBundle

_GATEWAY_BASE_URL_ENV = "AGENTIC_LAB_GATEWAY_BASE_URL"
_GATEWAY_API_KEY_ENV = "AGENTIC_LAB_GATEWAY_API_KEY"
_GATEWAY_CONFIG_PATH = Path("config/litellm/config.yaml")
_OUTPUT_ROOT = Path("artifacts/gateway-smoke/langgraph")
_EXPECTED_SCENARIO_COUNT = 5
_READINESS_PATH = "health/readiness"
_READINESS_ATTEMPTS = 20
_READINESS_DELAY_SECONDS = 1.0
_READINESS_REQUEST_TIMEOUT_SECONDS = 2.0


@dataclass(frozen=True, slots=True)
class GatewayConfigSummary:
    """Describe the committed gateway mapping without exposing credentials."""

    model_alias: str
    configured_upstream_model: str


@dataclass(frozen=True, slots=True)
class TokenUsage:
    """Represent standardized token usage for one gateway-backed execution."""

    input_tokens: int
    output_tokens: int
    total_tokens: int


@dataclass(frozen=True, slots=True)
class GatewaySmokeRun:
    """Capture one canonical scenario executed through the gateway boundary."""

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
    """Fail closed when the gateway smoke does not preserve required behavior."""

    passed: bool
    runs: int
    failures: tuple[str, ...]


def _required_gateway_environment_value(name: str) -> str:
    """Return one required non-blank gateway environment value."""
    value = os.environ.get(name)
    if value is None or not value.strip():
        raise RuntimeError(f"{name} must be configured for the gateway smoke")
    return value


def require_gateway_environment() -> tuple[str, str]:
    """Return the endpoint and client credential used by the LangChain adapter."""
    return (
        _required_gateway_environment_value(_GATEWAY_BASE_URL_ENV),
        _required_gateway_environment_value(_GATEWAY_API_KEY_ENV),
    )


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

    readiness_url = urljoin(base_url.rstrip("/") + "/", _READINESS_PATH)
    request = Request(
        readiness_url,
        headers={"Authorization": f"Bearer {api_key}"},
        method="GET",
    )
    last_error = "no response"

    for attempt in range(1, attempts + 1):
        try:
            with urlopen(
                request,
                timeout=_READINESS_REQUEST_TIMEOUT_SECONDS,
            ) as response:
                if response.status == 200:
                    return
                last_error = f"HTTP {response.status}"
        except OSError as exc:
            last_error = f"{type(exc).__name__}: {exc}"

        if attempt < attempts:
            sleep(delay_seconds)

    raise RuntimeError(
        "LiteLLM gateway did not become ready before the smoke started. "
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


def aggregate_usage(usage_by_model: Mapping[str, UsageMetadata]) -> TokenUsage:
    """Aggregate standardized LangChain token usage across callback entries."""
    return TokenUsage(
        input_tokens=sum(usage["input_tokens"] for usage in usage_by_model.values()),
        output_tokens=sum(usage["output_tokens"] for usage in usage_by_model.values()),
        total_tokens=sum(usage["total_tokens"] for usage in usage_by_model.values()),
    )


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


def run_gateway_smoke(
    scenarios: tuple[EvaluationScenario, ...],
    config: GatewayConfigSummary,
) -> tuple[GatewaySmokeRun, ...]:
    """Run every canonical scenario exactly once through LangGraph and LiteLLM."""
    if len(scenarios) != _EXPECTED_SCENARIO_COUNT:
        raise RuntimeError(f"Gateway smoke expected {_EXPECTED_SCENARIO_COUNT} scenarios")

    model = create_chat_model()
    analyzer = LangChainVulnerabilityAnalyzer(model)
    runs: list[GatewaySmokeRun] = []

    for scenario in scenarios:
        started_at = perf_counter()
        with get_usage_metadata_callback() as usage_callback:
            output = run_llm_analysis_graph_with_evidence(
                analyzer=analyzer,
                evidence_bundle=build_evidence_bundle(scenario),
            )
        latency_ms = (perf_counter() - started_at) * 1000
        usage = aggregate_usage(usage_callback.usage_metadata)
        result = output["result"]
        attempts = output["analysis_attempts"]

        run = GatewaySmokeRun(
            scenario_id=scenario.scenario_id,
            tags=scenario.tags,
            model_alias=config.model_alias,
            configured_upstream_model=config.configured_upstream_model,
            latency_ms=round(latency_ms, 2),
            analysis_source=output["analysis_source"],
            validation_passed=output["validation_passed"],
            analysis_attempts=attempts,
            model_calls=attempts,
            expected_match=matches_expected(scenario, result.assets),
            confidence=result.confidence,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            total_tokens=usage.total_tokens,
        )
        runs.append(run)
        print(json.dumps({"type": "gateway_smoke_run", **asdict(run)}))

    return tuple(runs)


def assess_gateway_smoke(runs: tuple[GatewaySmokeRun, ...]) -> SmokeAssessment:
    """Require correct final behavior plus observable model usage for every run."""
    failures: list[str] = []

    if len(runs) != _EXPECTED_SCENARIO_COUNT:
        failures.append("unexpected_run_count")

    for run in runs:
        if not run.expected_match:
            failures.append(f"{run.scenario_id}:expected_mismatch")
        if not run.validation_passed:
            failures.append(f"{run.scenario_id}:validation_failure")
        if run.model_calls < 1:
            failures.append(f"{run.scenario_id}:no_model_call")
        if run.total_tokens < 1:
            failures.append(f"{run.scenario_id}:missing_usage_metadata")

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
    """Render the human-readable non-baseline gateway smoke report."""
    lines = [
        "# LangGraph LiteLLM Gateway Smoke",
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
            "| Scenario | Expected match | Validation | Attempts | Calls | Tokens | "
            "Latency ms | Source |"
        ),
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]

    for run in runs:
        lines.append(
            "| "
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
                "This smoke verifies that the migrated LangGraph client can execute "
                "the canonical framework-neutral workload through the governed LiteLLM "
                "alias while preserving deterministic validation and expected truth."
            ),
            "",
            (
                "It is intentionally one execution per scenario and must not be used "
                "as a performance baseline or framework ranking."
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
    """Persist gateway smoke evidence outside official benchmark namespaces."""
    generated_at = datetime.now(UTC).isoformat()
    assessment = assess_gateway_smoke(runs)
    output_root.mkdir(parents=True, exist_ok=True)

    payload = {
        "schema_version": "1",
        "artifact_type": "gateway_smoke",
        "official_baseline": False,
        "review_status": "pending_manual_trace_review",
        "generated_at_utc": generated_at,
        "framework": "langgraph",
        "pattern": "evaluator_optimizer_via_litellm_proxy",
        "gateway_transport": "openai_compatible",
        "gateway_endpoint_persisted": False,
        "model_alias": config.model_alias,
        "configured_upstream_model": config.configured_upstream_model,
        "configured_upstream_evidence": "committed_litellm_config",
        "repetitions_per_scenario": 1,
        "scenario_count": len(runs),
        "runs": [asdict(run) for run in runs],
        "smoke_assessment": asdict(assessment),
    }

    json_path = output_root / "latest.json"
    markdown_path = output_root / "latest.md"
    json_path.write_text(json.dumps(payload, indent=2) + "\n")
    markdown_path.write_text(render_markdown(generated_at, config, runs, assessment))
    return json_path, markdown_path


def main() -> None:
    """Execute the provider-backed gateway smoke and persist reviewable evidence."""
    gateway_base_url, gateway_api_key = require_gateway_environment()
    wait_for_gateway_readiness(gateway_base_url, gateway_api_key)
    config = load_gateway_config_summary()
    scenarios = load_evaluation_scenarios()
    runs = run_gateway_smoke(scenarios=scenarios, config=config)
    assessment = assess_gateway_smoke(runs)
    json_path, markdown_path = write_smoke_artifacts(config=config, runs=runs)

    print(json.dumps({"type": "gateway_smoke_assessment", **asdict(assessment)}))
    print(f"artifact_json: {json_path}")
    print(f"artifact_markdown: {markdown_path}")

    if not assessment.passed:
        raise RuntimeError("LangGraph LiteLLM gateway smoke failed")


if __name__ == "__main__":
    main()
