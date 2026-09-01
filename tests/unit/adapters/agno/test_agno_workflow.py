"""Tests for the native Agno evaluator-optimizer Workflow."""

from agno.workflow import Condition, Loop, Step

from agentic_lab.adapters.agno.analyzer import AgnoUsage, AgnoVulnerabilityAnalyzer
from agentic_lab.adapters.agno.workflow import (
    AgnoWorkflowRuntime,
    _AgnoWorkflowState,
    _build_workflow,
)
from agentic_lab.adapters.fixtures.demo import (
    DEMO_CVE_ID,
    load_asset_inventory,
    load_security_policy,
    load_vulnerability_evidence,
)
from agentic_lab.application.contracts import AssetAssessment, LLMAnalysisDraft
from agentic_lab.application.evidence import AnalysisEvidenceBundle
from agentic_lab.application.validated_analysis import FALLBACK_RECOMMENDATION


class StubUsageRunner:
    """Provide structured drafts and isolated telemetry without provider calls."""

    def __init__(self, drafts: list[LLMAnalysisDraft]) -> None:
        self._drafts = drafts
        self.calls: list[tuple[str, str]] = []

    def run(self, system_prompt: str, user_prompt: str) -> LLMAnalysisDraft:
        self.calls.append((system_prompt, user_prompt))
        return self._drafts[len(self.calls) - 1]

    def consume_usage(self) -> AgnoUsage:
        model_calls = len(self.calls)
        return AgnoUsage(
            input_tokens=500 * model_calls,
            output_tokens=100 * model_calls,
            total_tokens=600 * model_calls,
            model_calls=model_calls,
        )


def _evidence_bundle() -> AnalysisEvidenceBundle:
    return {
        "vulnerability": load_vulnerability_evidence(DEMO_CVE_ID),
        "assets": load_asset_inventory(),
        "policy": load_security_policy(),
    }


def _correct_draft() -> LLMAnalysisDraft:
    return LLMAnalysisDraft(
        assets=(
            AssetAssessment(
                asset_id="api-prod-01",
                status="affected",
                rationale="Version 4.1 is below the exclusive 4.2 fixed boundary.",
            ),
            AssetAssessment(
                asset_id="api-prod-02",
                status="not_affected",
                rationale="Version 4.4 is not below the affected boundary.",
            ),
        ),
        recommendation="Upgrade the affected production asset.",
        confidence=0.97,
    )


def _wrong_draft() -> LLMAnalysisDraft:
    return LLMAnalysisDraft(
        assets=(
            AssetAssessment(
                asset_id="api-prod-01",
                status="not_affected",
                rationale="Incorrect test classification.",
            ),
            AssetAssessment(
                asset_id="api-prod-02",
                status="not_affected",
                rationale="Version 4.4 is outside the affected range.",
            ),
        ),
        recommendation="No action required.",
        confidence=0.6,
    )


def _runtime_with(
    drafts: list[LLMAnalysisDraft],
) -> tuple[AgnoWorkflowRuntime, StubUsageRunner]:
    runner = StubUsageRunner(drafts)

    def runner_factory(model_name: str) -> StubUsageRunner:
        assert model_name == "openai:gpt-5.6-luna"
        return runner

    return (
        AgnoWorkflowRuntime(
            "openai:gpt-5.6-luna",
            runner_factory=runner_factory,
        ),
        runner,
    )


def test_workflow_accepts_correct_first_draft_and_applies_policy() -> None:
    runtime, runner = _runtime_with([_correct_draft()])

    execution = runtime.run(_evidence_bundle())

    assert execution.output.analysis_source == "llm"
    assert execution.output.validation_passed is True
    assert execution.output.analysis_attempts == 1
    assert execution.output.result.requires_human_review is True
    assert [asset.status for asset in execution.output.result.assets] == [
        "affected",
        "not_affected",
    ]
    assert execution.usage.model_calls == 1
    assert len(runner.calls) == 1


def test_workflow_retries_with_evaluator_feedback_and_recovers() -> None:
    runtime, runner = _runtime_with([_wrong_draft(), _correct_draft()])

    execution = runtime.run(_evidence_bundle())

    assert execution.output.analysis_source == "llm"
    assert execution.output.validation_passed is True
    assert execution.output.analysis_attempts == 2
    assert execution.usage.model_calls == 2
    assert len(runner.calls) == 2
    assert "deterministic evaluator rejected" in runner.calls[1][1]
    assert "api-prod-01" in runner.calls[1][1]


def test_workflow_falls_back_after_two_invalid_drafts() -> None:
    runtime, runner = _runtime_with([_wrong_draft(), _wrong_draft()])

    execution = runtime.run(_evidence_bundle())

    assert execution.output.analysis_source == "oracle_fallback"
    assert execution.output.validation_passed is False
    assert execution.output.analysis_attempts == 2
    assert execution.output.result.confidence == 1.0
    assert execution.output.result.recommendation == FALLBACK_RECOMMENDATION
    assert [asset.status for asset in execution.output.result.assets] == [
        "affected",
        "not_affected",
    ]
    assert execution.usage.model_calls == 2
    assert len(runner.calls) == 2


def test_workflow_respects_single_attempt_limit() -> None:
    runtime, runner = _runtime_with([_wrong_draft()])

    execution = runtime.run(_evidence_bundle(), max_attempts=1)

    assert execution.output.analysis_source == "oracle_fallback"
    assert execution.output.analysis_attempts == 1
    assert execution.usage.model_calls == 1
    assert len(runner.calls) == 1


def test_runtime_returns_isolated_usage_for_retry_path() -> None:
    runtime, _ = _runtime_with([_wrong_draft(), _correct_draft()])

    execution = runtime.run(_evidence_bundle())

    assert execution.usage.input_tokens == 1000
    assert execution.usage.output_tokens == 200
    assert execution.usage.total_tokens == 1200
    assert execution.usage.model_calls == 2


def test_runtime_rejects_invalid_attempt_limit_before_creating_runner() -> None:
    calls: list[str] = []

    def runner_factory(model_name: str) -> StubUsageRunner:
        calls.append(model_name)
        return StubUsageRunner([_correct_draft()])

    runtime = AgnoWorkflowRuntime(
        "openai:gpt-5.6-luna",
        runner_factory=runner_factory,
    )

    try:
        runtime.run(_evidence_bundle(), max_attempts=0)
    except ValueError as exc:
        assert str(exc) == "max_attempts must be at least 1"
    else:
        raise AssertionError("Expected max_attempts=0 to be rejected")

    assert calls == []


def test_workflow_uses_native_loop_condition_and_disables_framework_retries() -> None:
    bundle = _evidence_bundle()
    runner = StubUsageRunner([_correct_draft()])
    state = _AgnoWorkflowState(
        vulnerability=bundle["vulnerability"],
        assets=bundle["assets"],
        policy=bundle["policy"],
        max_attempts=2,
        analyzer=AgnoVulnerabilityAnalyzer(runner),
    )

    workflow = _build_workflow(state)

    assert workflow.telemetry is False
    assert workflow.steps is not None
    assert len(workflow.steps) == 2

    analysis_loop = workflow.steps[0]
    final_route = workflow.steps[1]

    assert isinstance(analysis_loop, Loop)
    assert analysis_loop.max_iterations == 2
    assert analysis_loop.forward_iteration_output is False
    assert len(analysis_loop.steps) == 2
    assert all(isinstance(step, Step) for step in analysis_loop.steps)
    assert all(step.max_retries == 0 for step in analysis_loop.steps if isinstance(step, Step))

    assert isinstance(final_route, Condition)
    assert len(final_route.steps) == 1
    assert final_route.else_steps is not None
    assert len(final_route.else_steps) == 1
    assert isinstance(final_route.steps[0], Step)
    assert final_route.steps[0].max_retries == 0
    assert isinstance(final_route.else_steps[0], Step)
    assert final_route.else_steps[0].max_retries == 0
