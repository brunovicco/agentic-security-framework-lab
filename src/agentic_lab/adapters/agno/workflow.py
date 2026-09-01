"""Agno Workflow implementation of validated vulnerability analysis."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from agno.run import RunStatus
from agno.workflow import Condition, Loop, Step, Workflow
from agno.workflow.types import HumanReview, OnError, StepInput, StepOutput

from agentic_lab.adapters.agno.analyzer import (
    AgnoAnalysisRunner,
    AgnoRuntime,
    AgnoUsage,
    AgnoVulnerabilityAnalyzer,
)
from agentic_lab.application.analyzer import VulnerabilityAnalyzer
from agentic_lab.application.contracts import LLMAnalysisDraft
from agentic_lab.application.evidence import (
    AnalysisEvidenceBundle,
    AssetInventoryItem,
    SecurityPolicy,
    VulnerabilityEvidence,
)
from agentic_lab.application.oracle import assess_assets_deterministically
from agentic_lab.application.validated_analysis import (
    DEFAULT_MAX_ANALYSIS_ATTEMPTS,
    FALLBACK_RECOMMENDATION,
    DraftValidation,
    ValidatedAnalysisOutput,
    build_analysis_result,
    evaluate_human_review_policy,
    validate_analysis_draft,
)

AGNO_WORKFLOW_STEP_MAX_RETRIES = 0
AGNO_WORKFLOW_TELEMETRY = False


class _UsageAwareAgnoRunner(AgnoAnalysisRunner, Protocol):
    """Structured analysis runner that also exposes isolated usage telemetry."""

    def consume_usage(self) -> AgnoUsage:
        """Return usage accumulated by the current execution and reset it."""
        ...


RunnerFactory = Callable[[str], _UsageAwareAgnoRunner]


@dataclass(slots=True)
class _AgnoWorkflowState:
    """Hold application-owned state while Agno orchestrates control flow."""

    vulnerability: VulnerabilityEvidence
    assets: tuple[AssetInventoryItem, ...]
    policy: SecurityPolicy
    max_attempts: int
    analyzer: VulnerabilityAnalyzer
    analysis_attempts: int = 0
    feedback: str | None = None
    draft: LLMAnalysisDraft | None = None
    validation: DraftValidation | None = None
    output: ValidatedAnalysisOutput | None = None


@dataclass(frozen=True, slots=True)
class AgnoWorkflowExecution:
    """Return one validated Workflow result with framework LLM usage."""

    output: ValidatedAnalysisOutput
    usage: AgnoUsage


def _fail_closed_review() -> HumanReview:
    """Disable implicit skip behavior when a deterministic workflow step fails."""
    return HumanReview(on_error=OnError.fail)


def _analysis_step(state: _AgnoWorkflowState) -> Step:
    def execute(_: StepInput) -> StepOutput:
        if state.analysis_attempts >= state.max_attempts:
            raise RuntimeError("Agno Workflow attempted analysis beyond the configured bound")

        state.analysis_attempts += 1
        state.draft = state.analyzer.analyze(
            vulnerability=state.vulnerability,
            assets=state.assets,
            feedback=state.feedback,
        )
        return StepOutput(content=state.draft)

    return Step(
        name="Analyze vulnerability",
        executor=execute,
        max_retries=AGNO_WORKFLOW_STEP_MAX_RETRIES,
        skip_on_failure=False,
        human_review=_fail_closed_review(),
    )


def _validation_step(state: _AgnoWorkflowState) -> Step:
    def execute(_: StepInput) -> StepOutput:
        if state.draft is None:
            raise RuntimeError("Agno Workflow validation started without an LLM draft")

        state.validation = validate_analysis_draft(
            vulnerability=state.vulnerability,
            assets=state.assets,
            draft=state.draft,
        )
        state.feedback = None if state.validation.passed else state.validation.feedback
        return StepOutput(content=state.validation)

    return Step(
        name="Validate analysis",
        executor=execute,
        max_retries=AGNO_WORKFLOW_STEP_MAX_RETRIES,
        skip_on_failure=False,
        human_review=_fail_closed_review(),
    )


def _analysis_accepted(state: _AgnoWorkflowState) -> bool:
    return state.validation is not None and state.validation.passed


def _loop_end_condition(state: _AgnoWorkflowState) -> Callable[[list[StepOutput]], bool]:
    def end_condition(_: list[StepOutput]) -> bool:
        return _analysis_accepted(state)

    return end_condition


def _condition_evaluator(state: _AgnoWorkflowState) -> Callable[[StepInput], bool]:
    def evaluator(_: StepInput) -> bool:
        return _analysis_accepted(state)

    return evaluator


def _finalize_llm_step(state: _AgnoWorkflowState) -> Step:
    def execute(_: StepInput) -> StepOutput:
        if state.draft is None or state.validation is None or not state.validation.passed:
            raise RuntimeError("Agno Workflow cannot finalize an unvalidated LLM draft")

        requires_human_review = evaluate_human_review_policy(
            vulnerability=state.vulnerability,
            assets=state.assets,
            policy=state.policy,
            assessments=state.draft.assets,
        )
        result = build_analysis_result(
            vulnerability=state.vulnerability,
            assessments=state.draft.assets,
            recommendation=state.draft.recommendation,
            confidence=state.draft.confidence,
            requires_human_review=requires_human_review,
        )
        state.output = ValidatedAnalysisOutput(
            result=result,
            analysis_source="llm",
            validation_passed=True,
            validation_reason=state.validation.reason,
            analysis_attempts=state.analysis_attempts,
        )
        return StepOutput(content=state.output)

    return Step(
        name="Finalize accepted analysis",
        executor=execute,
        max_retries=AGNO_WORKFLOW_STEP_MAX_RETRIES,
        skip_on_failure=False,
        human_review=_fail_closed_review(),
    )


def _finalize_fallback_step(state: _AgnoWorkflowState) -> Step:
    def execute(_: StepInput) -> StepOutput:
        if state.validation is None:
            raise RuntimeError("Agno Workflow fallback started without an evaluator decision")

        assessments = assess_assets_deterministically(
            vulnerability=state.vulnerability,
            assets=state.assets,
        )
        requires_human_review = evaluate_human_review_policy(
            vulnerability=state.vulnerability,
            assets=state.assets,
            policy=state.policy,
            assessments=assessments,
        )
        result = build_analysis_result(
            vulnerability=state.vulnerability,
            assessments=assessments,
            recommendation=FALLBACK_RECOMMENDATION,
            confidence=1.0,
            requires_human_review=requires_human_review,
        )
        state.output = ValidatedAnalysisOutput(
            result=result,
            analysis_source="oracle_fallback",
            validation_passed=False,
            validation_reason=state.validation.reason,
            analysis_attempts=state.analysis_attempts,
        )
        return StepOutput(content=state.output)

    return Step(
        name="Finalize oracle fallback",
        executor=execute,
        max_retries=AGNO_WORKFLOW_STEP_MAX_RETRIES,
        skip_on_failure=False,
        human_review=_fail_closed_review(),
    )


def _build_workflow(state: _AgnoWorkflowState) -> Workflow:
    """Build one fresh native Agno Workflow around application-owned controls."""
    analysis_loop = Loop(
        name="Validated analysis loop",
        steps=[
            _analysis_step(state),
            _validation_step(state),
        ],
        max_iterations=state.max_attempts,
        end_condition=_loop_end_condition(state),
        forward_iteration_output=False,
        human_review=_fail_closed_review(),
    )

    final_route = Condition(
        name="Route validated result",
        evaluator=_condition_evaluator(state),
        steps=[_finalize_llm_step(state)],
        else_steps=[_finalize_fallback_step(state)],
        human_review=_fail_closed_review(),
    )

    return Workflow(
        name="Agno validated vulnerability analysis",
        steps=[analysis_loop, final_route],
        telemetry=AGNO_WORKFLOW_TELEMETRY,
        cache_session=False,
        add_workflow_history_to_steps=False,
    )


class AgnoWorkflowRuntime:
    """Execute evaluator-optimizer control flow using native Agno Workflow primitives."""

    def __init__(
        self,
        model_name: str,
        runner_factory: RunnerFactory = AgnoRuntime,
    ) -> None:
        """Store shared model identifier and per-execution runner factory."""
        self._model_name = model_name
        self._runner_factory = runner_factory

    def run(
        self,
        evidence_bundle: AnalysisEvidenceBundle,
        max_attempts: int = DEFAULT_MAX_ANALYSIS_ATTEMPTS,
    ) -> AgnoWorkflowExecution:
        """Execute one fresh Workflow and return validated output plus isolated usage."""
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")

        runner = self._runner_factory(self._model_name)
        analyzer = AgnoVulnerabilityAnalyzer(runner)
        state = _AgnoWorkflowState(
            vulnerability=evidence_bundle["vulnerability"],
            assets=evidence_bundle["assets"],
            policy=evidence_bundle["policy"],
            max_attempts=max_attempts,
            analyzer=analyzer,
        )
        workflow = _build_workflow(state)
        raw_output = workflow.run(input="validated vulnerability analysis")

        if raw_output.status == RunStatus.error:
            raise RuntimeError("Agno Workflow execution failed")
        if raw_output.status != RunStatus.completed:
            raise RuntimeError(f"Agno Workflow ended with unexpected status: {raw_output.status}")
        if state.output is None:
            raise RuntimeError("Agno Workflow ended without a validated analysis result")

        return AgnoWorkflowExecution(
            output=state.output,
            usage=runner.consume_usage(),
        )
