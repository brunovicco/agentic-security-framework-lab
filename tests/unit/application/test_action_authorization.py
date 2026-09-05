"""Tests for framework-neutral action authorization."""

import pytest
from pydantic import ValidationError

from agentic_lab.application.action_authorization import (
    ActionAuthorizer,
    ActionContext,
    AuthorizationOutcome,
    ProposedAction,
    StaticActionAuthorizationPolicy,
)

VULNERABILITY_RESOURCE = "CVE-2026-DEMO-001"
REMEDIATION_RESOURCE = "finding:demo-001"
REMEDIATION_AGENT = "remediation-agent"
OBSERVER_AGENT = "observer-agent"


def _authorizer() -> ActionAuthorizer:
    rules: dict[tuple[str, str, str, str], AuthorizationOutcome] = {
        (REMEDIATION_AGENT, "read_vulnerability", VULNERABILITY_RESOURCE, "test"): "allow",
        (OBSERVER_AGENT, "read_vulnerability", VULNERABILITY_RESOURCE, "test"): "deny",
        (REMEDIATION_AGENT, "modify_vulnerability", VULNERABILITY_RESOURCE, "test"): "deny",
        (
            REMEDIATION_AGENT,
            "create_remediation_task",
            REMEDIATION_RESOURCE,
            "production",
        ): "require_human_approval",
    }
    return StaticActionAuthorizationPolicy(rules)


def _context(caller_id: str = REMEDIATION_AGENT) -> ActionContext:
    return ActionContext(caller_id=caller_id)


def _vulnerability_action(action: str, environment: str = "test") -> ProposedAction:
    return ProposedAction(
        action=action,
        resource=VULNERABILITY_RESOURCE,
        environment=environment,
    )


def test_action_context_records_current_trusted_identity_source() -> None:
    """Record local composition as the only caller identity provenance currently proven."""
    context = _context()

    assert context.caller_id == REMEDIATION_AGENT
    assert context.identity_source == "trusted_composition"


def test_action_context_rejects_unimplemented_authenticated_identity_source() -> None:
    """Reject authentication-like provenance until a real trusted boundary implements it."""
    with pytest.raises(ValidationError, match="identity_source"):
        ActionContext.model_validate(
            {
                "caller_id": REMEDIATION_AGENT,
                "identity_source": "authenticated_principal",
            }
        )


def test_explicitly_allowed_action_is_allowed() -> None:
    """Allow only an exact caller/action/resource/environment policy match."""
    decision = _authorizer().authorize(
        _vulnerability_action("read_vulnerability"),
        _context(),
    )

    assert decision.outcome == "allow"
    assert decision.reason == "explicit_allow"


def test_explicitly_denied_action_is_denied() -> None:
    """Preserve an explicit deterministic deny decision for an exact scope."""
    decision = _authorizer().authorize(
        _vulnerability_action("modify_vulnerability"),
        _context(),
    )

    assert decision.outcome == "deny"
    assert decision.reason == "explicit_deny"


def test_same_action_scope_can_be_denied_for_different_caller() -> None:
    """Keep principal identity as an independent least-privilege dimension."""
    decision = _authorizer().authorize(
        _vulnerability_action("read_vulnerability"),
        _context(OBSERVER_AGENT),
    )

    assert decision.outcome == "deny"
    assert decision.reason == "explicit_deny"


def test_unknown_caller_fails_closed() -> None:
    """Deny an otherwise allowed action when no trusted caller rule matches."""
    decision = _authorizer().authorize(
        _vulnerability_action("read_vulnerability"),
        _context("unknown-agent"),
    )

    assert decision.outcome == "deny"
    assert decision.reason == "no_matching_rule"


def test_approval_gated_scope_requires_human_approval() -> None:
    """Keep an approval-gated production scope distinct from allow."""
    decision = _authorizer().authorize(
        ProposedAction(
            action="create_remediation_task",
            resource=REMEDIATION_RESOURCE,
            environment="production",
        ),
        _context(),
    )

    assert decision.outcome == "require_human_approval"
    assert decision.reason == "human_approval_required"


def test_unknown_action_fails_closed() -> None:
    """Deny action escalation even when caller, resource, and environment are known."""
    decision = _authorizer().authorize(
        _vulnerability_action("delete_vulnerability"),
        _context(),
    )

    assert decision.outcome == "deny"
    assert decision.reason == "no_matching_rule"


def test_unauthorized_resource_fails_closed() -> None:
    """Deny resource escalation for an otherwise allowed action."""
    decision = _authorizer().authorize(
        ProposedAction(
            action="read_vulnerability",
            resource="CVE-2026-DEMO-999",
            environment="test",
        ),
        _context(),
    )

    assert decision.outcome == "deny"
    assert decision.reason == "no_matching_rule"


def test_unauthorized_environment_fails_closed() -> None:
    """Deny environment escalation for an otherwise allowed action and resource."""
    decision = _authorizer().authorize(
        _vulnerability_action("read_vulnerability", environment="production"),
        _context(),
    )

    assert decision.outcome == "deny"
    assert decision.reason == "no_matching_rule"


def test_proposed_action_cannot_smuggle_caller_identity() -> None:
    """Reject model-adjacent attempts to declare the trusted caller identity."""
    with pytest.raises(ValidationError, match="caller_id"):
        ProposedAction.model_validate(
            {
                "action": "read_vulnerability",
                "resource": VULNERABILITY_RESOURCE,
                "environment": "test",
                "caller_id": REMEDIATION_AGENT,
            }
        )


def test_proposed_action_cannot_smuggle_identity_provenance() -> None:
    """Reject model-adjacent attempts to declare how trusted identity was established."""
    with pytest.raises(ValidationError, match="identity_source"):
        ProposedAction.model_validate(
            {
                "action": "read_vulnerability",
                "resource": VULNERABILITY_RESOURCE,
                "environment": "test",
                "identity_source": "trusted_composition",
            }
        )
