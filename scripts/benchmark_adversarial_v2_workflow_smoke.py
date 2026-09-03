"""Run a non-baseline adversarial v2 smoke across lightweight workflows."""

import argparse
import json
import os
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Literal, Protocol, cast

from agentic_lab.adapters.agno.workflow import AgnoWorkflowRuntime
from agentic_lab.adapters.crewai.flow import CrewAIFlowRuntime
from agentic_lab.adapters.fixtures.adversarial_v2_evidence import (
    load_adversarial_v2_evidence_scenarios,
)
from agentic_lab.adapters.llamaindex.workflow import LlamaIndexWorkflowRuntime
from agentic_lab.application.adversarial_reporting import (
    AdversarialRun,
    AdversarialRuntimeUsage,
    OverallSummary,
    ScenarioSummary,
    build_adversarial_run,
    render_adversarial_markdown_report,
    summarize_runs,
)
from agentic_lab.application.adversarial_v2 import (
    AdversarialEvidenceScenario,
    build_adversarial_v2_evidence_bundle,
)
from agentic_lab.application.evidence import AnalysisEvidenceBundle
from agentic_lab.application.validated_analysis import ValidatedAnalysisOutput

_MODEL_ENV = "AGENTIC_LAB_MODEL"
_SAMPLING = "provider_default"
_OUTPUT_ROOT = Path("artifacts/adversarial-v2-smoke")
_EXPECTED_SCENARIO_COUNT = 6

WorkflowKey = Literal[
    "crewai-flow",
    "llamaindex-workflow",
    "agno-workflow",
]


class _RuntimeUsage(Protocol):
    """Minimum normalized usage surface exposed by every workflow runtime."""

    input_tokens: int
    output_tokens: int
    total_tokens: int
    model_calls: int


class _WorkflowExecution(Protocol):
    """Minimum validated execution surface shared by the workflow runtimes."""

    output: ValidatedAnalysisOutput
    usage: _RuntimeUsage


class _WorkflowRuntime(Protocol):
    """Execute one evidence bundle through a lightweight framework workflow."""

    def run(
        self,
        evidence_bundle: AnalysisEvidenceBundle,
        max_attempts: int = 2,
    ) -> _WorkflowExecution:
        """Return validated output and isolated provider usage."""
        ...


RuntimeFactory = Callable[[str], _WorkflowRuntime]


@dataclass(frozen=True, slots=True)
class WorkflowSpec:
    """Describe one lightweight workflow without changing shared security semantics."""

    key: WorkflowKey
    display_name: str
    framework: str
    pattern: str
    runtime_factory: RuntimeFactory


@dataclass(frozen=True, slots=True)
class SmokeConfig:
    """Represent validated command-line selection for the smoke runner."""

    repetitions: int
    frameworks: tuple[WorkflowKey, ...]


@dataclass(frozen=True, slots=True)
class FrameworkSmokeResult:
    """Hold one framework's complete smoke output before persistence."""

    spec: WorkflowSpec
    runs: tuple[AdversarialRun, ...]
    scenario_summaries: tuple[ScenarioSummary, ...]
    overall: OverallSummary


@dataclass(frozen=True, slots=True)
class SmokeAssessment:
    """Fail-closed assessment of final task and security behavior."""

    passed: bool
    runs: int
    failures: tuple[str, ...]


def _crewai_runtime(model_name: str) -> _WorkflowRuntime:
    return cast(_WorkflowRuntime, CrewAIFlowRuntime(model_name))


def _llamaindex_runtime(model_name: str) -> _WorkflowRuntime:
    return cast(_WorkflowRuntime, LlamaIndexWorkflowRuntime(model_name))


def _agno_runtime(model_name: str) -> _WorkflowRuntime:
    return cast(_WorkflowRuntime, AgnoWorkflowRuntime(model_name))


_WORKFLOW_SPECS: dict[WorkflowKey, WorkflowSpec] = {
    "crewai-flow": WorkflowSpec(
        key="crewai-flow",
        display_name="CrewAI Flow",
        framework="crewai",
        pattern="flow_direct_llm_evaluator_optimizer_adversarial_v2_evidence_plane",
        runtime_factory=_crewai_runtime,
    ),
    "llamaindex-workflow": WorkflowSpec(
        key="llamaindex-workflow",
        display_name="LlamaIndex Workflow",
        framework="llamaindex",
        pattern="workflow_structured_predict_evaluator_optimizer_adversarial_v2_evidence_plane",
        runtime_factory=_llamaindex_runtime,
    ),
    "agno-workflow": WorkflowSpec(
        key="agno-workflow",
        display_name="Agno Workflow",
        framework="agno",
        pattern="workflow_loop_condition_evaluator_optimizer_adversarial_v2_evidence_plane",
        runtime_factory=_agno_runtime,
    ),
}
_DEFAULT_FRAMEWORKS: tuple[WorkflowKey, ...] = tuple(_WORKFLOW_SPECS)


def parse_config(argv: Sequence[str] | None = None) -> SmokeConfig:
    """Parse a one-repetition smoke selection and reject baseline-like runs."""
    parser = argparse.ArgumentParser(
        description=("Run a one-repetition adversarial v2 smoke across lightweight workflows."),
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=1,
        help="Executions per scenario. Smoke mode requires exactly one.",
    )
    parser.add_argument(
        "--framework",
        action="append",
        choices=tuple(_WORKFLOW_SPECS),
        help="Workflow to run. Repeat to select multiple; omit to run all three.",
    )
    args = parser.parse_args(argv)
    repetitions = cast(int, args.runs)
    raw_frameworks = cast(list[str] | None, args.framework)

    if repetitions != 1:
        raise ValueError("Smoke runner requires exactly one execution per scenario")

    selected = raw_frameworks or list(_DEFAULT_FRAMEWORKS)
    frameworks = tuple(dict.fromkeys(cast(list[WorkflowKey], selected)))
    return SmokeConfig(
        repetitions=repetitions,
        frameworks=frameworks,
    )


def require_model_name() -> str:
    """Return the model configured for every selected workflow."""
    model_name = os.environ.get(_MODEL_ENV)
    if not model_name:
        raise RuntimeError(f"{_MODEL_ENV} must identify the smoke model")
    return model_name


def configure_framework_telemetry() -> None:
    """Disable optional CrewAI tracing for the controlled headless smoke."""
    os.environ["CREWAI_TRACING_ENABLED"] = "false"


def _normalize_usage(usage: _RuntimeUsage) -> AdversarialRuntimeUsage:
    return AdversarialRuntimeUsage(
        model_calls=usage.model_calls,
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        total_tokens=usage.total_tokens,
    )


def run_framework_smoke(
    spec: WorkflowSpec,
    scenarios: tuple[AdversarialEvidenceScenario, ...],
    model_name: str,
) -> FrameworkSmokeResult:
    """Run all v2 scenarios once through one lightweight workflow runtime."""
    if len(scenarios) != _EXPECTED_SCENARIO_COUNT:
        raise RuntimeError(f"Adversarial v2 smoke expected {_EXPECTED_SCENARIO_COUNT} scenarios")

    runtime = spec.runtime_factory(model_name)
    all_runs: list[AdversarialRun] = []
    scenario_summaries: list[ScenarioSummary] = []

    for scenario in scenarios:
        evidence_bundle = build_adversarial_v2_evidence_bundle(scenario)
        started_at = perf_counter()
        execution = runtime.run(evidence_bundle=evidence_bundle)
        latency_ms = (perf_counter() - started_at) * 1000
        run = build_adversarial_run(
            scenario=scenario,
            iteration=1,
            model_name=model_name,
            latency_ms=latency_ms,
            output=execution.output,
            usage=_normalize_usage(execution.usage),
        )
        all_runs.append(run)
        print(json.dumps({"type": "run", "workflow": spec.key, **asdict(run)}))

        summary = ScenarioSummary(
            scenario_id=scenario.scenario_id,
            attack_class=scenario.attack_class,
            tags=scenario.tags,
            metrics=summarize_runs([run]),
        )
        scenario_summaries.append(summary)
        print(
            json.dumps(
                {
                    "type": "scenario_summary",
                    "workflow": spec.key,
                    **asdict(summary),
                }
            )
        )

    overall = OverallSummary(
        framework=spec.framework,
        pattern=spec.pattern,
        model=model_name,
        scenarios=len(scenarios),
        metrics=summarize_runs(all_runs),
    )
    return FrameworkSmokeResult(
        spec=spec,
        runs=tuple(all_runs),
        scenario_summaries=tuple(scenario_summaries),
        overall=overall,
    )


def assess_framework_smoke(result: FrameworkSmokeResult) -> SmokeAssessment:
    """Require every final result to preserve task and security invariants."""
    failures: list[str] = []

    if len(result.runs) != _EXPECTED_SCENARIO_COUNT:
        failures.append("unexpected_run_count")

    for run in result.runs:
        if not run.task_match:
            failures.append(f"{run.scenario_id}:task_mismatch")
        if not run.security_passed:
            failures.append(f"{run.scenario_id}:security_failure")
        if run.unsafe_acceptance:
            failures.append(f"{run.scenario_id}:unsafe_acceptance")

    return SmokeAssessment(
        passed=not failures,
        runs=len(result.runs),
        failures=tuple(failures),
    )


def write_smoke_artifacts(
    result: FrameworkSmokeResult,
    model_name: str,
    output_root: Path = _OUTPUT_ROOT,
) -> tuple[Path, Path]:
    """Persist isolated smoke artifacts outside the official baseline namespace."""
    generated_at = datetime.now(UTC).isoformat()
    output_dir = output_root / result.spec.key
    output_dir.mkdir(parents=True, exist_ok=True)
    assessment = assess_framework_smoke(result)
    payload = {
        "schema_version": "1",
        "suite_version": "2",
        "artifact_type": "smoke",
        "official_baseline": False,
        "review_status": "pending_manual_trace_review",
        "generated_at_utc": generated_at,
        "workflow": result.spec.key,
        "framework": result.spec.framework,
        "pattern": result.spec.pattern,
        "model": model_name,
        "sampling": _SAMPLING,
        "repetitions_per_scenario": 1,
        "scenario_count": len(result.scenario_summaries),
        "runs": [asdict(run) for run in result.runs],
        "scenario_summaries": [asdict(summary) for summary in result.scenario_summaries],
        "overall_summary": asdict(result.overall),
        "smoke_assessment": asdict(assessment),
    }

    json_path = output_dir / "latest.json"
    markdown_path = output_dir / "latest.md"
    json_path.write_text(json.dumps(payload, indent=2) + "\n")
    markdown_path.write_text(
        render_adversarial_markdown_report(
            title=f"{result.spec.display_name} Adversarial Security Evaluation v2 Smoke",
            generated_at_utc=generated_at,
            model_name=model_name,
            framework=result.spec.framework,
            pattern=result.spec.pattern,
            scenario_summaries=list(result.scenario_summaries),
            overall=result.overall,
            smoke=True,
        )
    )
    return json_path, markdown_path


def main() -> None:
    """Execute selected provider-backed smokes and persist non-baseline artifacts."""
    config = parse_config()
    model_name = require_model_name()
    configure_framework_telemetry()
    scenarios = load_adversarial_v2_evidence_scenarios()
    failed_workflows: list[str] = []

    for workflow_key in config.frameworks:
        spec = _WORKFLOW_SPECS[workflow_key]
        print(json.dumps({"type": "workflow_start", "workflow": workflow_key}))
        result = run_framework_smoke(
            spec=spec,
            scenarios=scenarios,
            model_name=model_name,
        )
        assessment = assess_framework_smoke(result)
        json_path, markdown_path = write_smoke_artifacts(
            result=result,
            model_name=model_name,
        )
        print(
            json.dumps(
                {
                    "type": "smoke_assessment",
                    "workflow": workflow_key,
                    **asdict(assessment),
                }
            )
        )
        print(f"artifact_json: {json_path}")
        print(f"artifact_markdown: {markdown_path}")

        if not assessment.passed:
            failed_workflows.append(workflow_key)

    if failed_workflows:
        joined = ", ".join(failed_workflows)
        raise RuntimeError(f"Adversarial v2 smoke failed for: {joined}")


if __name__ == "__main__":
    main()
