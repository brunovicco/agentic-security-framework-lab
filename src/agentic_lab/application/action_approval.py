"""Framework-neutral trusted human approval contracts for governed actions."""

from datetime import UTC, datetime
from typing import Literal, Protocol, Self

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from agentic_lab.application.action_authorization import ActionContext, ProposedAction

ApprovalStatus = Literal[
    "not_applicable",
    "missing",
    "invalid",
    "unauthorized_approver",
    "not_yet_valid",
    "expired",
    "revoked",
    "validated",
]
ApprovalClaimStatus = Literal["missing", "claimed", "revoked"]


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


class ApprovalClaim(BaseModel):
    """Record whether one approval claim found usable, revoked, or no evidence."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    status: ApprovalClaimStatus
    approval: HumanApprovalEvidence | None = None

    @model_validator(mode="after")
    def validate_claim_evidence(self) -> Self:
        """Keep claim status and attached human evidence structurally consistent."""
        if self.status == "missing" and self.approval is not None:
            raise ValueError("missing approval claim cannot contain approval evidence")
        if self.status != "missing" and self.approval is None:
            raise ValueError(f"{self.status} approval claim requires approval evidence")
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
    ) -> ApprovalClaim:
        """Atomically return one explicit single-use claim outcome for the requested scope."""
        ...


class ActionApprovalRevoker(Protocol):
    """Revoke an unclaimed approval capability through a trusted control-plane boundary."""

    def revoke_approval(self, approval_id: str) -> bool:
        """Return True only when one still-unclaimed approval transitions to revoked."""
        ...


class NoActionApprovalProvider:
    """Fail-closed approval provider used when no HITL source is configured."""

    def claim_approval(
        self,
        proposed_action: ProposedAction,
        context: ActionContext,
    ) -> ApprovalClaim:
        """Return an explicit missing claim so approval-required actions remain blocked."""
        return ApprovalClaim(status="missing")


NULL_ACTION_APPROVAL_PROVIDER: ActionApprovalProvider = NoActionApprovalProvider()
