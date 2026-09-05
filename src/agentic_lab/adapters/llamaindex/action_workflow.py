"""LlamaIndex Workflow adapter for framework-neutral governed action execution."""

import asyncio
from typing import cast

from workflows import Workflow, step
from workflows.events import StartEvent, StopEvent

from agentic_lab.application.action_authorization import ActionContext, ProposedAction
from agentic_lab.application.action_runtime import (
    ActionExecutionEvidence,
    GovernedActionRuntime,
)


class GovernedActionStartEvent(StartEvent):
    """Carry only model-safe proposed action input into the Workflow."""

    proposed_action: ProposedAction


class LlamaIndexGovernedActionWorkflow(Workflow):
    """Orchestrate one governed action without owning authorization semantics."""

    def __init__(
        self,
        runtime: GovernedActionRuntime,
        context: ActionContext,
        *,
        timeout: float | None = 10.0,
    ) -> None:
        """Bind trusted application dependencies outside Workflow event data."""
        super().__init__(timeout=timeout, verbose=False)
        self._action_runtime = runtime
        self._context = context

    @step
    async def execute_governed_action(self, ev: GovernedActionStartEvent) -> StopEvent:
        """Delegate authorization and enforcement to the application runtime."""
        evidence = self._action_runtime.execute(
            ev.proposed_action,
            self._context,
        )
        return StopEvent(result=evidence)


class LlamaIndexGovernedActionRuntime:
    """Run governed actions through a fresh LlamaIndex Workflow instance."""

    def __init__(
        self,
        runtime: GovernedActionRuntime,
        context: ActionContext,
    ) -> None:
        """Store trusted application dependencies outside Workflow input events."""
        self._action_runtime = runtime
        self._context = context

    async def arun(self, proposed_action: ProposedAction) -> ActionExecutionEvidence:
        """Execute one proposed action asynchronously through LlamaIndex Workflow."""
        workflow = LlamaIndexGovernedActionWorkflow(
            runtime=self._action_runtime,
            context=self._context,
        )
        raw_output = cast(
            object,
            await workflow.run(
                start_event=GovernedActionStartEvent(proposed_action=proposed_action)
            ),
        )
        if not isinstance(raw_output, ActionExecutionEvidence):
            raise RuntimeError(
                "LlamaIndex governed action Workflow ended without execution evidence"
            )
        return raw_output

    def run(self, proposed_action: ProposedAction) -> ActionExecutionEvidence:
        """Run from synchronous code; async applications should call arun()."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.arun(proposed_action))

        raise RuntimeError(
            "LlamaIndexGovernedActionRuntime.run() cannot be used inside an active event loop; "
            "use arun()"
        )
