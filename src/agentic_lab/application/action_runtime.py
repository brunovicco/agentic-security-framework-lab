"""Framework-neutral runtime enforcement for proposed agent actions."""

from typing import Protocol

from pydantic import BaseModel, ConfigDict

from agentic_lab.application.action_approval import (
    NULL_ACTION_APPROVAL_PROVIDER,
    SYSTEM_APPROVAL_CLOCK,
    ActionApprovalProvider,
    ApprovalClock,
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
        approval_clock: ApprovalClock = SYSTEM_APPROVAL_CLOCK,
    ) -> None:
        """Bind policy, trusted HITL evidence, time, and execution boundaries."""
        self._authorizer = authorizer
        self._executor = executor
        self._approval_provider = approval_provider
        self._approval_clock = approval_clock

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
            approval = self._approval_provider.claim_approval(proposed_action, context)
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

            now = self._approval_clock.now()
            if now.tzinfo is None or now.utcoffset() is None:
                raise RuntimeError("approval clock must return timezone-aware current time")

            if now < approval.approved_at:
                return ActionExecutionEvidence(
                    proposed_action=proposed_action,
                    context=context,
                    authorization=decision,
                    approval_status="not_yet_valid",
                    human_approval=approval,
                    execution_occurred=False,
                )

            if now >= approval.expires_at:
                return ActionExecutionEvidence(
                    proposed_action=proposed_action,
                    context=context,
                    authorization=decision,
                    approval_status="expired",
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
