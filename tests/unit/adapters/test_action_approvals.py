"""Tests for the deterministic in-memory action approval provider."""

from datetime import UTC, datetime, timedelta

import pytest

from agentic_lab.adapters.fixtures.action_approvals import InMemoryActionApprovalProvider
from agentic_lab.application.action_approval import ApprovalClaim, HumanApprovalEvidence
from agentic_lab.application.action_authorization import (
    ActionContext,
    CallerIdentitySource,
    ProposedAction,
)

FINDING_RESOURCE = "finding:demo-001"
APPROVED_AT = datetime(2026, 9, 5, 20, 0, tzinfo=UTC)
EXPIRES_AT = APPROVED_AT + timedelta(minutes=15)


def _action(resource: str = FINDING_RESOURCE) -> ProposedAction:
    return ProposedAction(
        action="acknowledge_finding",
        resource=resource,
        environment="production",
    )


def _context(
    caller_id: str = "remediation-agent",
    identity_source: CallerIdentitySource = "trusted_composition",
) -> ActionContext:
    return ActionContext(caller_id=caller_id, identity_source=identity_source)


def _approval(
    approval_id: str = "approval-001",
    identity_source: CallerIdentitySource = "trusted_composition",
) -> HumanApprovalEvidence:
    return HumanApprovalEvidence(
        approval_id=approval_id,
        approver_id="soc-reviewer",
        proposed_action=_action(),
        context=_context(identity_source=identity_source),
        approved_at=APPROVED_AT,
        expires_at=EXPIRES_AT,
    )


def test_empty_provider_does_not_auto_approve() -> None:
    """Require approval evidence to be supplied explicitly."""
    provider = InMemoryActionApprovalProvider()

    assert provider.claim_approval(_action(), _context()) == ApprovalClaim(status="missing")


def test_exact_scope_claims_explicitly_supplied_approval_once() -> None:
    """Remove the claimed approval so the same capability cannot be replayed."""
    approval = _approval()
    provider = InMemoryActionApprovalProvider([approval])

    assert provider.claim_approval(_action(), _context()) == ApprovalClaim(
        status="claimed",
        approval=approval,
    )
    assert provider.claim_approval(_action(), _context()) == ApprovalClaim(status="missing")


def test_different_resource_or_caller_does_not_claim_approval() -> None:
    """Prevent approval reuse across resource or principal boundaries."""
    approval = _approval()
    provider = InMemoryActionApprovalProvider([approval])

    assert provider.claim_approval(
        _action("finding:demo-999"),
        _context(),
    ) == ApprovalClaim(status="missing")
    assert provider.claim_approval(_action(), _context("observer-agent")) == ApprovalClaim(
        status="missing"
    )
    assert provider.claim_approval(_action(), _context()) == ApprovalClaim(
        status="claimed",
        approval=approval,
    )


def test_different_identity_source_does_not_claim_or_consume_approval() -> None:
    """Keep one caller id isolated across trusted identity provenance boundaries."""
    approval = _approval(identity_source="trusted_composition")
    provider = InMemoryActionApprovalProvider([approval])

    assert provider.claim_approval(
        _action(),
        _context(identity_source="api_key"),
    ) == ApprovalClaim(status="missing")
    assert provider.claim_approval(
        _action(),
        _context(identity_source="trusted_composition"),
    ) == ApprovalClaim(status="claimed", approval=approval)


def test_distinct_approvals_can_authorize_distinct_executions_of_same_scope() -> None:
    """Preserve multiple deliberate approvals while consuming each exactly once."""
    first = _approval("approval-001")
    second = _approval("approval-002")
    provider = InMemoryActionApprovalProvider([first, second])

    assert provider.claim_approval(_action(), _context()) == ApprovalClaim(
        status="claimed",
        approval=first,
    )
    assert provider.claim_approval(_action(), _context()) == ApprovalClaim(
        status="claimed",
        approval=second,
    )
    assert provider.claim_approval(_action(), _context()) == ApprovalClaim(status="missing")


def test_unclaimed_approval_can_be_revoked_once_and_never_claimed_as_usable() -> None:
    """Turn one still-unused capability into sticky revoked evidence before execution."""
    approval = _approval()
    provider = InMemoryActionApprovalProvider([approval])

    assert provider.revoke_approval(approval.approval_id) is True
    assert provider.revoke_approval(approval.approval_id) is False
    assert provider.claim_approval(_action(), _context()) == ApprovalClaim(
        status="revoked",
        approval=approval,
    )
    assert provider.claim_approval(_action(), _context()) == ApprovalClaim(status="missing")
    assert provider.revoke_approval(approval.approval_id) is False


def test_claimed_approval_cannot_be_retroactively_revoked() -> None:
    """Keep revocation limited to authority not yet transferred to a runtime attempt."""
    approval = _approval()
    provider = InMemoryActionApprovalProvider([approval])

    assert provider.claim_approval(_action(), _context()) == ApprovalClaim(
        status="claimed",
        approval=approval,
    )
    assert provider.revoke_approval(approval.approval_id) is False


def test_revoking_one_approval_does_not_revoke_distinct_capability_for_same_scope() -> None:
    """Target revocation by immutable approval id rather than broad action scope."""
    first = _approval("approval-001")
    second = _approval("approval-002")
    provider = InMemoryActionApprovalProvider([first, second])

    assert provider.revoke_approval(first.approval_id) is True
    assert provider.claim_approval(_action(), _context()) == ApprovalClaim(
        status="revoked",
        approval=first,
    )
    assert provider.claim_approval(_action(), _context()) == ApprovalClaim(
        status="claimed",
        approval=second,
    )


def test_revoked_and_claimed_lifecycle_is_isolated_by_identity_source() -> None:
    """Keep lifecycle state independent across source-specific approval queues."""
    trusted = _approval("approval-trusted", identity_source="trusted_composition")
    api_key = _approval("approval-api-key", identity_source="api_key")
    provider = InMemoryActionApprovalProvider([trusted, api_key])

    assert provider.revoke_approval(trusted.approval_id) is True
    assert provider.claim_approval(
        _action(),
        _context(identity_source="api_key"),
    ) == ApprovalClaim(status="claimed", approval=api_key)
    assert provider.claim_approval(
        _action(),
        _context(identity_source="trusted_composition"),
    ) == ApprovalClaim(status="revoked", approval=trusted)


def test_unknown_approval_id_cannot_be_revoked() -> None:
    """Do not manufacture revocation state for approval capabilities that do not exist."""
    provider = InMemoryActionApprovalProvider([_approval()])

    assert provider.revoke_approval("approval-unknown") is False


def test_duplicate_approval_id_is_rejected() -> None:
    """Do not let duplicated trusted evidence manufacture reusable approval capacity."""
    with pytest.raises(ValueError, match="duplicate approval_id"):
        InMemoryActionApprovalProvider([_approval(), _approval()])
