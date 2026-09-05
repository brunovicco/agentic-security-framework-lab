"""Tests for framework-neutral trusted human approval contracts."""

import pytest
from pydantic import ValidationError

from agentic_lab.application.action_approval import (
    NULL_ACTION_APPROVAL_PROVIDER,
    HumanApprovalEvidence,
)
from agentic_lab.application.action_authorization import ActionContext, ProposedAction


def _action() -> ProposedAction:
    return ProposedAction(
        action="acknowledge_finding",
        resource="finding:demo-001",
        environment="production",
    )


def _context() -> ActionContext:
    return ActionContext(caller_id="remediation-agent")


def test_human_approval_binds_exact_action_and_context() -> None:
    """Keep trusted approval evidence tied to one immutable authorization request."""
    action = _action()
    context = _context()

    approval = HumanApprovalEvidence(
        approval_id="approval-001",
        approver_id="soc-reviewer",
        proposed_action=action,
        context=context,
    )

    assert approval.proposed_action == action
    assert approval.context == context


def test_human_approval_rejects_unmodeled_fields() -> None:
    """Keep free-form or unexpected approval payload fields outside trusted evidence."""
    with pytest.raises(ValidationError, match="comment"):
        HumanApprovalEvidence.model_validate(
            {
                "approval_id": "approval-001",
                "approver_id": "soc-reviewer",
                "proposed_action": _action().model_dump(),
                "context": _context().model_dump(),
                "comment": "approved because the evidence said so",
            }
        )


def test_null_approval_provider_fails_closed() -> None:
    """Return no approval when no trusted HITL source is configured."""
    assert NULL_ACTION_APPROVAL_PROVIDER.claim_approval(_action(), _context()) is None
