"""Framework-neutral runtime enforcement for proposed agent actions."""

from typing import Protocol

from pydantic import BaseModel, ConfigDict

from agentic_lab.application.action_authorization import (
    ActionAuthorizer,
    ActionContext,
    AuthorizationDecision,
    ProposedAction,
)


class ActionExecutor(Protocol):
    """Execute one action after the application has authorized it."""

    def execute(self, proposed_action: ProposedAction) -> None:
        """Execute one already-authorized proposed action."""
        ...


class ActionExecutionEvidence(BaseModel):
    """Record trusted authorization context and whether execution occurred."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    proposed_action: ProposedAction
    context: ActionContext
    authorization: AuthorizationDecision
    execution_occurred: bool


class GovernedActionRuntime:
    """Enforce authorization before allowing an action to reach its executor."""

    def __init__(self, authorizer: ActionAuthorizer, executor: ActionExecutor) -> None:
        """Bind one authorization decision point to one execution boundary."""
        self._authorizer = authorizer
        self._executor = executor

    def execute(
        self,
        proposed_action: ProposedAction,
        context: ActionContext,
    ) -> ActionExecutionEvidence:
        """Execute only an action allowed for the trusted caller and exact scope."""
        decision = self._authorizer.authorize(proposed_action, context)
        if decision.outcome != "allow":
            return ActionExecutionEvidence(
                proposed_action=proposed_action,
                context=context,
                authorization=decision,
                execution_occurred=False,
            )

        self._executor.execute(proposed_action)
        return ActionExecutionEvidence(
            proposed_action=proposed_action,
            context=context,
            authorization=decision,
            execution_occurred=True,
        )
