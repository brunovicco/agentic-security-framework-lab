"""Provider-free tests for the adversarial v2 workflow baseline runner."""

import json
from dataclasses import dataclass, replace
from pathlib import Path
from runpy import run_path
from typing import Any

import pytest

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
    str(Path(__file__).parents[2] / "scripts" / "benchmark_adversarial_v2_workflow_baseline.py")
)
WorkflowSpec: Any = _SCRIPT["WorkflowSpec"]
assess_framework_baseline: Any = _SCRIPT["assess_framework_baseline"]
parse_config: Any = _SCRIPT["parse_config"]
run_framework_baseline: Any = _SCRIPT["run_framework_baseline"]
write_baseline_candidate_artifacts: Any = _SCRIPT["write_baseline_candidate_artifacts"]


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
    """Exercise shared validation while recording every repeated evidence bundle."""

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


def _run_three_repetitions(runtime: StubWorkflowRuntime) -> Any:
    return run_framework_baseline(
        spec=_spec(runtime),
        scenarios=load_adversarial_v2_evidence_scenarios(),
        model_name="openai:test-model",
        repetitions=3,
    )


def test_parse_config_defaults_to_three_runs_for_all_workflows() -> None:
    config = parse_config([])

    assert config.repetitions == 3
    assert config.frameworks == (
        "crewai-flow",
        "llamaindex-workflow",
        "agno-workflow",
    )


def test_parse_config_deduplicates_explicit_workflow_selection() -> None:
    config = parse_config(
        [
            "--runs",
            "2",
            "--framework",
            "agno-workflow",
            "--framework",
            "agno-workflow",
            "--framework",
            "crewai-flow",
        ]
    )

    assert config.repetitions == 2
    assert config.frameworks == ("agno-workflow", "crewai-flow")


def test_parse_config_rejects_smoke_sized_execution() -> None:
    with pytest.raises(ValueError, match="at least two"):
        parse_config(["--runs", "1"])


def test_baseline_repeats_every_v2_scenario_and_preserves_iteration_identity() -> None:
    runtime = StubWorkflowRuntime()

    result = _run_three_repetitions(runtime)
    assessment = assess_framework_baseline(result)

    assert assessment.passed is True
    assert assessment.runs == 18
    assert assessment.failures == ()
    assert len(runtime.bundles) == 18
    assert len(result.scenario_summaries) == 6
    assert all(bundle.get("documents") for bundle in runtime.bundles)
    assert all(len(run.attempt_trace) == run.analysis_attempts for run in result.runs)
    assert all(run.task_match for run in result.runs)
    assert all(run.security_passed for run in result.runs)
    assert all(not run.unsafe_acceptance for run in result.runs)

    iterations_by_scenario = {
        scenario_id: [run.iteration for run in result.runs if run.scenario_id == scenario_id]
        for scenario_id in {run.scenario_id for run in result.runs}
    }
    assert all(iterations == [1, 2, 3] for iterations in iterations_by_scenario.values())


def test_baseline_assessment_fails_closed_with_iteration_specific_failure() -> None:
    runtime = StubWorkflowRuntime()
    result = _run_three_repetitions(runtime)
    first = replace(
        result.runs[0],
        task_match=False,
        security_passed=False,
        unsafe_acceptance=True,
    )
    failed = replace(result, runs=(first, *result.runs[1:]))

    assessment = assess_framework_baseline(failed)

    assert assessment.passed is False
    assert assessment.failures == (
        f"{first.scenario_id}:{first.iteration}:task_mismatch",
        f"{first.scenario_id}:{first.iteration}:security_failure",
        f"{first.scenario_id}:{first.iteration}:unsafe_acceptance",
    )


def test_repeated_artifacts_remain_candidates_until_manual_trace_review(
    tmp_path: Path,
) -> None:
    runtime = StubWorkflowRuntime()
    result = _run_three_repetitions(runtime)

    json_path, markdown_path = write_baseline_candidate_artifacts(
        result=result,
        model_name="openai:test-model",
        output_root=tmp_path,
    )

    payload = json.loads(json_path.read_text())
    markdown = markdown_path.read_text()

    assert payload["artifact_type"] == "baseline_candidate"
    assert payload["official_baseline"] is False
    assert payload["review_status"] == "pending_manual_trace_review"
    assert payload["repetitions_per_scenario"] == 3
    assert payload["scenario_count"] == 6
    assert len(payload["runs"]) == 18
    assert payload["baseline_assessment"]["passed"] is True
    assert "baseline candidate" in markdown.lower()
    assert "not an official baseline" in markdown.lower()
