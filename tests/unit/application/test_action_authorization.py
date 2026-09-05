"""Tests for framework-neutral action authorization."""

from agentic_lab.application.action_authorization import (
    ActionAuthorizer,
    AuthorizationOutcome,
    ProposedAction,
    StaticActionAuthorizationPolicy,
)


def _authorizer() -> ActionAuthorizer:
    rules: dict[str, AuthorizationOutcome] = {
        "read_vulnerability": "allow",
        "modify_vulnerability": "deny",
        "create_remediation_task": "require_human_approval",
    }
    return StaticActionAuthorizationPolicy(rules)


def test_explicitly_allowed_action_is_allowed() -> None:
    """Allow an action only when trusted policy explicitly allows it."""
    decision = _authorizer().authorize(ProposedAction(action="read_vulnerability"))

    assert decision.outcome == "allow"
    assert decision.reason == "explicit_allow"


def test_explicitly_denied_action_is_denied() -> None:
    """Preserve an explicit deterministic deny decision."""
    decision = _authorizer().authorize(ProposedAction(action="modify_vulnerability"))

    assert decision.outcome == "deny"
    assert decision.reason == "explicit_deny"


def test_approval_gated_action_requires_human_approval() -> None:
    """Keep approval-required distinct from authorization to execute."""
    decision = _authorizer().authorize(ProposedAction(action="create_remediation_task"))

    assert decision.outcome == "require_human_approval"
    assert decision.reason == "human_approval_required"


def test_unknown_action_fails_closed() -> None:
    """Deny an action when no trusted authorization rule matches it."""
    decision = _authorizer().authorize(ProposedAction(action="delete_vulnerability"))

    assert decision.outcome == "deny"
    assert decision.reason == "no_matching_rule"
