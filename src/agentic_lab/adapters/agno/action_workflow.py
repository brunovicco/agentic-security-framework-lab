"""Agno Workflow adapter for framework-neutral governed action execution."""

from dataclasses import dataclass

from agno.run import RunStatus
from agno.workflow import Step, Workflow
from agno.workflow.types import HumanReview, OnError, StepInput, StepOutput

from agentic_lab.application.action_authorization import ActionContext, ProposedAction
from agentic_lab.application.action_runtime import (
    ActionExecutionEvidence,
    GovernedActionExecutionError,
    GovernedActionRuntime,
)

AGNO_ACTION_WORKFLOW_STEP_MAX_RETRIES = 0
AGNO_ACTION_WORKFLOW_TELEMETRY = False


@dataclass(slots=True)
class _AgnoGovernedActionState:
    """Bridge application-owned execution outcomes across Agno orchestration."""

    proposed_action: ProposedAction
    execution_evidence: ActionExecutionEvidence | None = None
    execution_error: GovernedActionExecutionError | None = None


def _fail_closed_review() -> HumanReview:
    """Fail the workflow instead of silently skipping a failed mutable step."""
    return HumanReview(on_error=OnError.fail)


def _action_step(
    state: _AgnoGovernedActionState,
    action_runtime: GovernedActionRuntime,
    context: ActionContext,
) -> Step:
    """Build one native Agno Step around the application-owned runtime."""

    def execute(_: StepInput) -> StepOutput:
        try:
            evidence = action_runtime.execute(
                state.proposed_action,
                context,
            )
        except GovernedActionExecutionError as exc:
            state.execution_error = exc
            raise

        state.execution_evidence = evidence
        return StepOutput(content=evidence)

    return Step(
        name="Execute governed action",
        executor=execute,
        max_retries=AGNO_ACTION_WORKFLOW_STEP_MAX_RETRIES,
        skip_on_failure=False,
        human_review=_fail_closed_review(),
    )


def _build_workflow(
    state: _AgnoGovernedActionState,
    action_runtime: GovernedActionRuntime,
    context: ActionContext,
) -> Workflow:
    """Build a fresh native Agno Workflow without policy or enforcement logic."""
    return Workflow(
        name="Agno governed action execution",
        steps=[_action_step(state, action_runtime, context)],
        telemetry=AGNO_ACTION_WORKFLOW_TELEMETRY,
        cache_session=False,
        add_workflow_history_to_steps=False,
    )


class AgnoGovernedActionRuntime:
    """Run proposed actions through Agno while the application owns authority."""

    def __init__(
        self,
        runtime: GovernedActionRuntime,
        context: ActionContext,
    ) -> None:
        """Bind trusted application dependencies outside workflow input."""
        self._action_runtime = runtime
        self._context = context

    def run(self, proposed_action: ProposedAction) -> ActionExecutionEvidence:
        """Execute one fresh Agno Workflow and return application evidence."""
        state = _AgnoGovernedActionState(proposed_action=proposed_action)
        workflow = _build_workflow(
            state,
            self._action_runtime,
            self._context,
        )
        raw_output = workflow.run(input="governed action execution")

        if raw_output.status == RunStatus.error:
            if state.execution_error is not None:
                raise state.execution_error
            raise RuntimeError("Agno governed action Workflow execution failed")
        if raw_output.status != RunStatus.completed:
            raise RuntimeError(
                f"Agno governed action Workflow ended with unexpected status: {raw_output.status}"
            )
        if state.execution_evidence is None:
            raise RuntimeError("Agno governed action Workflow ended without execution evidence")

        return state.execution_evidence
