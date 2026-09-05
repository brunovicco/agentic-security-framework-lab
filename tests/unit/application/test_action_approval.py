"""Tests for framework-neutral trusted human approval contracts."""

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from agentic_lab.application.action_approval import (
    NULL_ACTION_APPROVAL_PROVIDER,
    HumanApprovalEvidence,
)
from agentic_lab.application.action_authorization import ActionContext, ProposedAction

APPROVED_AT = datetime(2026, 9, 5, 20, 0, tzinfo=timezone.utc)
EXPIRES_AT = APPROVED_AT + timedelta(minutes=15)


def _action() -> ProposedAction:
    return ProposedAction(
        action="acknowledge_finding",
        resource="finding:demo-001",
        environment="production",
    )


def _context() -> ActionContext:
    return ActionContext(caller_id="remediation-agent")


def test_human_approval_binds_exact_action_context_and_time_window() -> None:
    """Tie trusted approval to one immutable request and bounded validity window."""
    action = _action()
    context = _context()

    approval = HumanApprovalEvidence(
        approval_id="approval-001",
        approver_id="soc-reviewer",
        proposed_action=action,
        context=context,
        approved_at=APPROVED_AT,
        expires_at=EXPIRES_AT,
    )

    assert approval.proposed_action == action
    assert approval.context == context
    assert approval.approved_at == APPROVED_AT
    assert approval.expires_at == EXPIRES_AT


@pytest.mark.parametrize(
    ("approved_at", "expires_at"),
    [
        (APPROVED_AT, APPROVED_AT),
        (EXPIRES_AT, APPROVED_AT),
    ],
)
def test_human_approval_rejects_empty_or_reversed_time_window(
    approved_at: datetime,
    expires_at: datetime,
) -> None:
    """Reject approval evidence without a positive temporal validity interval."""
    with pytest.raises(ValidationError, match="expires_at must be later than approved_at"):
        HumanApprovalEvidence(
            approval_id="approval-001",
            approver_id="soc-reviewer",
            proposed_action=_action(),
            context=_context(),
            approved_at=approved_at,
            expires_at=expires_at,
        )


@pytest.mark.parametrize("field", ["approved_at", "expires_at"])
def test_human_approval_requires_timezone_aware_timestamps(field: str) -> None:
    """Reject naive approval timestamps before they enter trusted evidence."""
    payload = {
        "approval_id": "approval-001",
        "approver_id": "soc-reviewer",
        "proposed_action": _action(),
        "context": _context(),
        "approved_at": APPROVED_AT,
        "expires_at": EXPIRES_AT,
    }
    payload[field] = datetime(2026, 9, 5, 20, 0)

    with pytest.raises(ValidationError):
        HumanApprovalEvidence.model_validate(payload)


def test_human_approval_rejects_unmodeled_fields() -> None:
    """Keep free-form or unexpected approval payload fields outside trusted evidence."""
    with pytest.raises(ValidationError, match="comment"):
        HumanApprovalEvidence.model_validate(
            {
                "approval_id": "approval-001",
                "approver_id": "soc-reviewer",
                "proposed_action": _action().model_dump(),
                "context": _context().model_dump(),
                "approved_at": APPROVED_AT,
                "expires_at": EXPIRES_AT,
                "comment": "approved because the evidence said so",
            }
        )


def test_null_approval_provider_fails_closed() -> None:
    """Return no approval when no trusted HITL source is configured."""
    assert NULL_ACTION_APPROVAL_PROVIDER.claim_approval(_action(), _context()) is None
