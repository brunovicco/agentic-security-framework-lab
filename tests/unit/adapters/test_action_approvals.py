"""Tests for the deterministic in-memory action approval provider."""

import pytest

from agentic_lab.adapters.fixtures.action_approvals import InMemoryActionApprovalProvider
from agentic_lab.application.action_approval import HumanApprovalEvidence
from agentic_lab.application.action_authorization import ActionContext, ProposedAction

FINDING_RESOURCE = "finding:demo-001"


def _action(resource: str = FINDING_RESOURCE) -> ProposedAction:
    return ProposedAction(
        action="acknowledge_finding",
        resource=resource,
        environment="production",
    )


def _context(caller_id: str = "remediation-agent") -> ActionContext:
    return ActionContext(caller_id=caller_id)


def _approval(
    approval_id: str = "approval-001",
) -> HumanApprovalEvidence:
    return HumanApprovalEvidence(
        approval_id=approval_id,
        approver_id="soc-reviewer",
        proposed_action=_action(),
        context=_context(),
    )


def test_empty_provider_does_not_auto_approve() -> None:
    """Require approval evidence to be supplied explicitly."""
    provider = InMemoryActionApprovalProvider()

    assert provider.claim_approval(_action(), _context()) is None


def test_exact_scope_claims_explicitly_supplied_approval_once() -> None:
    """Remove the claimed approval so the same capability cannot be replayed."""
    approval = _approval()
    provider = InMemoryActionApprovalProvider([approval])

    assert provider.claim_approval(_action(), _context()) == approval
    assert provider.claim_approval(_action(), _context()) is None


def test_different_resource_or_caller_does_not_claim_approval() -> None:
    """Prevent approval reuse across resource or principal boundaries."""
    approval = _approval()
    provider = InMemoryActionApprovalProvider([approval])

    assert provider.claim_approval(_action("finding:demo-999"), _context()) is None
    assert provider.claim_approval(_action(), _context("observer-agent")) is None
    assert provider.claim_approval(_action(), _context()) == approval


def test_distinct_approvals_can_authorize_distinct_executions_of_same_scope() -> None:
    """Preserve multiple deliberate approvals while consuming each exactly once."""
    first = _approval("approval-001")
    second = _approval("approval-002")
    provider = InMemoryActionApprovalProvider([first, second])

    assert provider.claim_approval(_action(), _context()) == first
    assert provider.claim_approval(_action(), _context()) == second
    assert provider.claim_approval(_action(), _context()) is None


def test_duplicate_approval_id_is_rejected() -> None:
    """Do not let duplicated trusted evidence manufacture reusable approval capacity."""
    with pytest.raises(ValueError, match="duplicate approval_id"):
        InMemoryActionApprovalProvider([_approval(), _approval()])
