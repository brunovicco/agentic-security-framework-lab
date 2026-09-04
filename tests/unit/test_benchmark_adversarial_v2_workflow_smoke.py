"""Provider-free tests for the adversarial v2 workflow smoke runner."""

import json
import os
from dataclasses import dataclass, replace
from pathlib import Path
from runpy import run_path
from typing import Any

import pytest
from pytest import MonkeyPatch

from agentic_lab.adapters.fixtures.adversarial_v2_evidence import (
    load_adversarial_v2_evidence_scenarios,
)
from agentic_lab.application.contracts import LLMAnalysisDraft
from agentic_lab.application.evidence import (
    AnalysisEvidenceBundle,
    AssetInventoryItem,
    VulnerabilityEvidence,
)
from agentic_lab.application.oracle import assess_assets_deterministically
from agentic_lab.application.validated_analysis import (
    ValidatedAnalysisOutput,
    run_validated_analysis,
)

_SCRIPT = run_path(
    str(Path(__file__).parents[2] / "scripts" / "benchmark_adversarial_v2_workflow_smoke.py")
)
WorkflowSpec: Any = _SCRIPT["WorkflowSpec"]
assess_framework_smoke: Any = _SCRIPT["assess_framework_smoke"]
configure_framework_telemetry: Any = _SCRIPT["configure_framework_telemetry"]
parse_config: Any = _SCRIPT["parse_config"]
require_direct_model_name: Any = _SCRIPT["require_direct_model_name"]
run_framework_smoke: Any = _SCRIPT["run_framework_smoke"]
workflow_model_name: Any = _SCRIPT["workflow_model_name"]
write_smoke_artifacts: Any = _SCRIPT["write_smoke_artifacts"]


@dataclass(frozen=True, slots=True)
class StubUsage:
    input_tokens: int
    output_tokens: int
    total_tokens: int
    model_calls: int


@dataclass(frozen=True, slots=True)
class StubExecution:
    output: ValidatedAnalysisOutput
    usage: StubUsage


class OracleDraftAnalyzer:
    """Return task-correct drafts without consuming textual instructions."""

    def analyze(
        self,
        vulnerability: VulnerabilityEvidence,
        assets: tuple[AssetInventoryItem, ...],
        feedback: str | None = None,
    ) -> LLMAnalysisDraft:
        assert feedback is None
        return LLMAnalysisDraft(
            assets=assess_assets_deterministically(
                vulnerability=vulnerability,
                assets=assets,
            ),
            recommendation="Apply the validated vendor remediation.",
            confidence=0.9,
        )


class StubWorkflowRuntime:
    """Exercise the shared validator while recording complete evidence bundles."""

    def __init__(self) -> None:
        self.bundles: list[AnalysisEvidenceBundle] = []

    def run(
        self,
        evidence_bundle: AnalysisEvidenceBundle,
        max_attempts: int = 2,
    ) -> StubExecution:
        self.bundles.append(evidence_bundle)
        output = run_validated_analysis(
            analyzer=OracleDraftAnalyzer(),
            evidence_bundle=evidence_bundle,
            max_attempts=max_attempts,
        )
        return StubExecution(
            output=output,
            usage=StubUsage(
                input_tokens=100,
                output_tokens=20,
                total_tokens=120,
                model_calls=output.analysis_attempts,
            ),
        )


def _spec(runtime: StubWorkflowRuntime) -> Any:
    def factory(model_name: str) -> StubWorkflowRuntime:
        assert model_name == "openai:test-model"
        return runtime

    return WorkflowSpec(
        key="agno-workflow",
        display_name="Test Workflow",
        framework="test-framework",
        pattern="test_pattern_adversarial_v2_evidence_plane",
        runtime_factory=factory,
    )


def test_parse_config_defaults_to_all_workflows_once() -> None:
    config = parse_config([])

    assert config.repetitions == 1
    assert config.frameworks == (
        "crewai-flow",
        "llamaindex-workflow",
        "agno-workflow",
    )


def test_parse_config_deduplicates_explicit_workflow_selection() -> None:
    config = parse_config(
        [
            "--framework",
            "agno-workflow",
            "--framework",
            "agno-workflow",
            "--framework",
            "crewai-flow",
        ]
    )

    assert config.frameworks == ("agno-workflow", "crewai-flow")


def test_parse_config_rejects_repeated_baseline_like_execution() -> None:
    with pytest.raises(ValueError, match="requires exactly one"):
        parse_config(["--runs", "3"])


def test_llamaindex_smoke_uses_gateway_alias_without_direct_model_env(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.delenv("AGENTIC_LAB_MODEL", raising=False)

    assert require_direct_model_name(("llamaindex-workflow",)) is None
    assert workflow_model_name("llamaindex-workflow", None) == "security-analysis"


def test_agno_smoke_still_requires_direct_model_env(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.delenv("AGENTIC_LAB_MODEL", raising=False)

    with pytest.raises(RuntimeError, match="direct-provider model for Agno"):
        require_direct_model_name(("agno-workflow",))


def test_configure_framework_telemetry_disables_crewai_tracing(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("CREWAI_TRACING_ENABLED", "true")

    configure_framework_telemetry()

    assert os.environ["CREWAI_TRACING_ENABLED"] == "false"


def test_smoke_uses_all_v2_documents_and_builds_complete_traces() -> None:
    runtime = StubWorkflowRuntime()
    scenarios = load_adversarial_v2_evidence_scenarios()

    result = run_framework_smoke(
        spec=_spec(runtime),
        scenarios=scenarios,
        model_name="openai:test-model",
    )
    assessment = assess_framework_smoke(result)

    assert assessment.passed is True
    assert assessment.runs == 6
    assert assessment.failures == ()
    assert len(runtime.bundles) == 6
    assert all(bundle.get("documents") for bundle in runtime.bundles)
    assert all(len(run.attempt_trace) == run.analysis_attempts for run in result.runs)
    assert all(run.task_match for run in result.runs)
    assert all(run.security_passed for run in result.runs)
    assert all(not run.unsafe_acceptance for run in result.runs)


def test_smoke_assessment_fails_closed_on_final_invariant_failure() -> None:
    runtime = StubWorkflowRuntime()
    result = run_framework_smoke(
        spec=_spec(runtime),
        scenarios=load_adversarial_v2_evidence_scenarios(),
        model_name="openai:test-model",
    )
    first = replace(
        result.runs[0],
        task_match=False,
        security_passed=False,
        unsafe_acceptance=True,
    )
    failed = replace(result, runs=(first, *result.runs[1:]))

    assessment = assess_framework_smoke(failed)

    assert assessment.passed is False
    assert assessment.failures == (
        f"{first.scenario_id}:task_mismatch",
        f"{first.scenario_id}:security_failure",
        f"{first.scenario_id}:unsafe_acceptance",
    )


def test_smoke_artifacts_are_explicitly_non_baseline(
    tmp_path: Path,
) -> None:
    runtime = StubWorkflowRuntime()
    result = run_framework_smoke(
        spec=_spec(runtime),
        scenarios=load_adversarial_v2_evidence_scenarios(),
        model_name="openai:test-model",
    )

    json_path, markdown_path = write_smoke_artifacts(
        result=result,
        model_name="openai:test-model",
        output_root=tmp_path,
    )

    payload = json.loads(json_path.read_text())
    markdown = markdown_path.read_text()

    assert payload["artifact_type"] == "smoke"
    assert payload["official_baseline"] is False
    assert payload["review_status"] == "pending_manual_trace_review"
    assert payload["repetitions_per_scenario"] == 1
    assert payload["scenario_count"] == 6
    assert payload["smoke_assessment"]["passed"] is True
    assert "pending manual trace review" in markdown
    assert "not an" in markdown
    assert "official baseline" in markdown
