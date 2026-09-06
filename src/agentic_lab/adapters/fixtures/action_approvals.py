"""Deterministic in-memory approval provider for controlled HITL experiments."""

from collections import defaultdict, deque
from collections.abc import Iterable
from typing import Literal

from agentic_lab.application.action_approval import ApprovalClaim, HumanApprovalEvidence
from agentic_lab.application.action_authorization import (
    ActionContext,
    CallerIdentitySource,
    ProposedAction,
)

ApprovalKey = tuple[str, CallerIdentitySource, str, str, str]
ApprovalLifecycleState = Literal["available", "revoked", "claimed"]


def _approval_key(
    proposed_action: ProposedAction,
    context: ActionContext,
) -> ApprovalKey:
    return (
        context.caller_id,
        context.identity_source,
        proposed_action.action,
        proposed_action.resource,
        proposed_action.environment,
    )


class InMemoryActionApprovalProvider:
    """Claim or revoke explicitly supplied synthetic approval capabilities."""

    def __init__(self, approvals: Iterable[HumanApprovalEvidence] = ()) -> None:
        """Load trusted approval evidence without allowing duplicate approval IDs."""
        queues: defaultdict[ApprovalKey, deque[HumanApprovalEvidence]] = defaultdict(deque)
        approval_states: dict[str, ApprovalLifecycleState] = {}

        for approval in approvals:
            if approval.approval_id in approval_states:
                raise ValueError(f"duplicate approval_id: {approval.approval_id}")
            approval_states[approval.approval_id] = "available"
            queues[_approval_key(approval.proposed_action, approval.context)].append(approval)

        self._approvals = dict(queues)
        self._approval_states = approval_states

    def claim_approval(
        self,
        proposed_action: ProposedAction,
        context: ActionContext,
    ) -> ApprovalClaim:
        """Remove and report one approval capability for the exact requested scope."""
        key = _approval_key(proposed_action, context)
        approvals = self._approvals.get(key)
        if not approvals:
            return ApprovalClaim(status="missing")

        approval = approvals.popleft()
        if not approvals:
            del self._approvals[key]

        state = self._approval_states[approval.approval_id]
        if state == "revoked":
            return ApprovalClaim(status="revoked", approval=approval)
        if state != "available":
            raise RuntimeError(f"approval is not claimable: {approval.approval_id}")

        self._approval_states[approval.approval_id] = "claimed"
        return ApprovalClaim(status="claimed", approval=approval)

    def revoke_approval(self, approval_id: str) -> bool:
        """Revoke one exact approval only while its single-use capability is unclaimed."""
        if self._approval_states.get(approval_id) != "available":
            return False

        self._approval_states[approval_id] = "revoked"
        return True
