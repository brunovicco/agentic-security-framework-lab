"""CrewAI Flow adapter for framework-neutral governed action execution."""

from typing import cast

from crewai.flow.flow import Flow, start
from pydantic import BaseModel

from agentic_lab.application.action_authorization import ActionContext, ProposedAction
from agentic_lab.application.action_runtime import (
    ActionExecutionEvidence,
    GovernedActionRuntime,
)


class CrewAIGovernedActionState(BaseModel):
    """Store only model-safe action workflow state inside CrewAI Flow."""

    proposed_action: ProposedAction
    execution_evidence: ActionExecutionEvidence | None = None


class CrewAIGovernedActionFlow(Flow[CrewAIGovernedActionState]):
    """Orchestrate one governed action without owning authorization semantics."""

    suppress_flow_events: bool = True

    def __init__(
        self,
        *,
        runtime: GovernedActionRuntime,
        context: ActionContext,
        proposed_action: ProposedAction,
    ) -> None:
        """Bind trusted application dependencies outside model-controlled Flow state."""
        super().__init__(
            initial_state=CrewAIGovernedActionState(proposed_action=proposed_action),
            tracing=False,
        )
        self._runtime = runtime
        self._context = context

    @start()
    def execute_governed_action(self) -> ActionExecutionEvidence:
        """Delegate authorization and enforcement to the application runtime."""
        evidence = self._runtime.execute(
            self.state.proposed_action,
            self._context,
        )
        self.state.execution_evidence = evidence
        return evidence


def run_governed_action_flow(
    runtime: GovernedActionRuntime,
    context: ActionContext,
    proposed_action: ProposedAction,
) -> ActionExecutionEvidence:
    """Run one proposed action through CrewAI Flow and return application evidence."""
    flow = CrewAIGovernedActionFlow(
        runtime=runtime,
        context=context,
        proposed_action=proposed_action,
    )
    cast(object, flow.kickoff())

    evidence = flow.state.execution_evidence
    if evidence is None:
        raise RuntimeError("CrewAI governed action Flow ended without execution evidence")
    return evidence
