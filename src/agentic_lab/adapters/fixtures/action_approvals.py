"""Deterministic in-memory approval provider for controlled HITL experiments."""

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
    """Return only explicitly supplied approvals for exact action scopes."""

    def __init__(self, approvals: Iterable[HumanApprovalEvidence] = ()) -> None:
        """Load trusted synthetic approval evidence without auto-approving actions."""
        self._approvals = {
            _approval_key(approval.proposed_action, approval.context): approval
            for approval in approvals
        }

    def find_approval(
        self,
        proposed_action: ProposedAction,
        context: ActionContext,
    ) -> HumanApprovalEvidence | None:
        """Resolve one explicitly supplied approval for the exact requested scope."""
        return self._approvals.get(_approval_key(proposed_action, context))
