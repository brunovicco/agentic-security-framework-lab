"""Framework-neutral runtime enforcement for proposed agent actions."""

from typing import Protocol

from pydantic import BaseModel, ConfigDict

from agentic_lab.application.action_approval import (
    NULL_ACTION_APPROVAL_PROVIDER,
    ActionApprovalProvider,
    ApprovalStatus,
    HumanApprovalEvidence,
)
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
    """Record authorization, approval, and execution outcomes independently."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    proposed_action: ProposedAction
    context: ActionContext
    authorization: AuthorizationDecision
    approval_status: ApprovalStatus
    human_approval: HumanApprovalEvidence | None
    execution_occurred: bool


class GovernedActionRuntime:
    """Enforce authorization and trusted approval before action execution."""

    def __init__(
        self,
        authorizer: ActionAuthorizer,
        executor: ActionExecutor,
        approval_provider: ActionApprovalProvider = NULL_ACTION_APPROVAL_PROVIDER,
    ) -> None:
        """Bind policy, optional trusted HITL evidence, and execution boundaries."""
        self._authorizer = authorizer
        self._executor = executor
        self._approval_provider = approval_provider

    def execute(
        self,
        proposed_action: ProposedAction,
        context: ActionContext,
    ) -> ActionExecutionEvidence:
        """Execute only after policy and any required trusted approval are satisfied."""
        decision = self._authorizer.authorize(proposed_action, context)

        if decision.outcome == "deny":
            return ActionExecutionEvidence(
                proposed_action=proposed_action,
                context=context,
                authorization=decision,
                approval_status="not_applicable",
                human_approval=None,
                execution_occurred=False,
            )

        if decision.outcome == "require_human_approval":
            approval = self._approval_provider.find_approval(proposed_action, context)
            if approval is None:
                return ActionExecutionEvidence(
                    proposed_action=proposed_action,
                    context=context,
                    authorization=decision,
                    approval_status="missing",
                    human_approval=None,
                    execution_occurred=False,
                )

            if approval.proposed_action != proposed_action or approval.context != context:
                return ActionExecutionEvidence(
                    proposed_action=proposed_action,
                    context=context,
                    authorization=decision,
                    approval_status="invalid",
                    human_approval=approval,
                    execution_occurred=False,
                )

            self._executor.execute(proposed_action)
            return ActionExecutionEvidence(
                proposed_action=proposed_action,
                context=context,
                authorization=decision,
                approval_status="validated",
                human_approval=approval,
                execution_occurred=True,
            )

        self._executor.execute(proposed_action)
        return ActionExecutionEvidence(
            proposed_action=proposed_action,
            context=context,
            authorization=decision,
            approval_status="not_applicable",
            human_approval=None,
            execution_occurred=True,
        )
