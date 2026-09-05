"""Deterministic in-memory approval provider for controlled HITL experiments."""

from collections import defaultdict, deque
from collections.abc import Iterable

from agentic_lab.application.action_approval import HumanApprovalEvidence
from agentic_lab.application.action_authorization import ActionContext, ProposedAction

ApprovalKey = tuple[str, str, str, str]


def _approval_key(
    proposed_action: ProposedAction,
    context: ActionContext,
) -> ApprovalKey:
    return (
        context.caller_id,
        proposed_action.action,
        proposed_action.resource,
        proposed_action.environment,
    )


class InMemoryActionApprovalProvider:
    """Claim explicitly supplied synthetic approvals as single-use capabilities."""

    def __init__(self, approvals: Iterable[HumanApprovalEvidence] = ()) -> None:
        """Load trusted approval evidence without allowing duplicate approval IDs."""
        queues: defaultdict[ApprovalKey, deque[HumanApprovalEvidence]] = defaultdict(deque)
        seen_approval_ids: set[str] = set()

        for approval in approvals:
            if approval.approval_id in seen_approval_ids:
                raise ValueError(f"duplicate approval_id: {approval.approval_id}")
            seen_approval_ids.add(approval.approval_id)
            queues[_approval_key(approval.proposed_action, approval.context)].append(approval)

        self._approvals = dict(queues)

    def claim_approval(
        self,
        proposed_action: ProposedAction,
        context: ActionContext,
    ) -> HumanApprovalEvidence | None:
        """Remove and return one approval for the exact scope so it cannot be replayed."""
        key = _approval_key(proposed_action, context)
        approvals = self._approvals.get(key)
        if not approvals:
            return None

        approval = approvals.popleft()
        if not approvals:
            del self._approvals[key]
        return approval
