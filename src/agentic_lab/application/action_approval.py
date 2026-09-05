"""Framework-neutral trusted human approval contracts for governed actions."""

from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

from agentic_lab.application.action_authorization import ActionContext, ProposedAction

ApprovalStatus = Literal[
    "not_applicable",
    "missing",
    "invalid",
    "validated",
]


class HumanApprovalEvidence(BaseModel):
    """Represent trusted human approval bound to one exact caller and action scope."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    approval_id: str = Field(min_length=1)
    approver_id: str = Field(min_length=1)
    proposed_action: ProposedAction
    context: ActionContext


class ActionApprovalProvider(Protocol):
    """Resolve trusted human approval evidence for one exact action request."""

    def find_approval(
        self,
        proposed_action: ProposedAction,
        context: ActionContext,
    ) -> HumanApprovalEvidence | None:
        """Return trusted approval evidence or no approval for the requested scope."""
        ...


class NoActionApprovalProvider:
    """Fail-closed approval provider used when no HITL source is configured."""

    def find_approval(
        self,
        proposed_action: ProposedAction,
        context: ActionContext,
    ) -> HumanApprovalEvidence | None:
        """Return no approval so approval-required actions remain blocked."""
        return None


NULL_ACTION_APPROVAL_PROVIDER: ActionApprovalProvider = NoActionApprovalProvider()
