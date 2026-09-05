"""Tests for the deterministic in-memory action approval provider."""

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


def _approval() -> HumanApprovalEvidence:
    return HumanApprovalEvidence(
        approval_id="approval-001",
        approver_id="soc-reviewer",
        proposed_action=_action(),
        context=_context(),
    )


def test_empty_provider_does_not_auto_approve() -> None:
    """Require approval evidence to be supplied explicitly."""
    provider = InMemoryActionApprovalProvider()

    assert provider.find_approval(_action(), _context()) is None


def test_exact_scope_returns_explicitly_supplied_approval() -> None:
    """Resolve approval only for its exact caller/action/resource/environment scope."""
    approval = _approval()
    provider = InMemoryActionApprovalProvider([approval])

    assert provider.find_approval(_action(), _context()) == approval


def test_different_resource_or_caller_does_not_reuse_approval() -> None:
    """Prevent approval reuse across resource or principal boundaries."""
    provider = InMemoryActionApprovalProvider([_approval()])

    assert provider.find_approval(_action("finding:demo-999"), _context()) is None
    assert provider.find_approval(_action(), _context("observer-agent")) is None
