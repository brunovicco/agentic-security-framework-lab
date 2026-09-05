"""Framework-neutral trusted human approval contracts for governed actions."""

from datetime import UTC, datetime
from typing import Literal, Protocol, Self

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from agentic_lab.application.action_authorization import ActionContext, ProposedAction

ApprovalStatus = Literal[
    "not_applicable",
    "missing",
    "invalid",
    "not_yet_valid",
    "expired",
    "validated",
]


class HumanApprovalEvidence(BaseModel):
    """Represent trusted human approval bound to one exact caller, action, and time window."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    approval_id: str = Field(min_length=1)
    approver_id: str = Field(min_length=1)
    proposed_action: ProposedAction
    context: ActionContext
    approved_at: AwareDatetime
    expires_at: AwareDatetime

    @model_validator(mode="after")
    def validate_temporal_window(self) -> Self:
        """Require one non-empty validity window for trusted approval evidence."""
        if self.expires_at <= self.approved_at:
            raise ValueError("expires_at must be later than approved_at")
        return self


class ApprovalClock(Protocol):
    """Provide trusted current time for approval freshness validation."""

    def now(self) -> datetime:
        """Return one timezone-aware current time value."""
        ...


class UtcApprovalClock:
    """Use timezone-aware UTC wall-clock time outside deterministic tests."""

    def now(self) -> datetime:
        """Return the current UTC time."""
        return datetime.now(UTC)


SYSTEM_APPROVAL_CLOCK: ApprovalClock = UtcApprovalClock()


class ActionApprovalProvider(Protocol):
    """Claim trusted human approval evidence for one exact action request."""

    def claim_approval(
        self,
        proposed_action: ProposedAction,
        context: ActionContext,
    ) -> HumanApprovalEvidence | None:
        """Atomically return one unused approval at most once for the requested scope."""
        ...


class NoActionApprovalProvider:
    """Fail-closed approval provider used when no HITL source is configured."""

    def claim_approval(
        self,
        proposed_action: ProposedAction,
        context: ActionContext,
    ) -> HumanApprovalEvidence | None:
        """Return no approval so approval-required actions remain blocked."""
        return None


NULL_ACTION_APPROVAL_PROVIDER: ActionApprovalProvider = NoActionApprovalProvider()
