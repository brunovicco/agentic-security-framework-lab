"""Framework-neutral runtime enforcement for proposed agent actions."""

from typing import Protocol

from pydantic import BaseModel, ConfigDict

from agentic_lab.application.action_authorization import (
    ActionAuthorizer,
    AuthorizationDecision,
    ProposedAction,
)


class ActionExecutor(Protocol):
    """Execute one action after the application has authorized it."""

    def execute(self, proposed_action: ProposedAction) -> None:
        """Execute one already-authorized proposed action."""
        ...


class ActionExecutionEvidence(BaseModel):
    """Record authorization and whether the action reached its executor."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    proposed_action: ProposedAction
    authorization: AuthorizationDecision
    execution_occurred: bool


class GovernedActionRuntime:
    """Enforce authorization before allowing an action to reach its executor."""

    def __init__(self, authorizer: ActionAuthorizer, executor: ActionExecutor) -> None:
        """Bind one authorization decision point to one execution boundary."""
        self._authorizer = authorizer
        self._executor = executor

    def execute(self, proposed_action: ProposedAction) -> ActionExecutionEvidence:
        """Execute only an explicitly allowed action and record the enforced result."""
        decision = self._authorizer.authorize(proposed_action)
        if decision.outcome != "allow":
            return ActionExecutionEvidence(
                proposed_action=proposed_action,
                authorization=decision,
                execution_occurred=False,
            )

        self._executor.execute(proposed_action)
        return ActionExecutionEvidence(
            proposed_action=proposed_action,
            authorization=decision,
            execution_occurred=True,
        )
