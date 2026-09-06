"""Tests for framework-neutral action authorization."""

import pytest
from pydantic import ValidationError

from agentic_lab.application.action_authorization import (
    ActionAuthorizationRuleKey,
    ActionAuthorizer,
    ActionContext,
    AuthorizationDecision,
    AuthorizationOutcome,
    CallerIdentitySource,
    ProposedAction,
    StaticActionAuthorizationPolicy,
)

VULNERABILITY_RESOURCE = "CVE-2026-DEMO-001"
REMEDIATION_RESOURCE = "finding:demo-001"
REMEDIATION_AGENT = "remediation-agent"
OBSERVER_AGENT = "observer-agent"


def _authorizer() -> ActionAuthorizer:
    rules: dict[ActionAuthorizationRuleKey, AuthorizationOutcome] = {
        (
            REMEDIATION_AGENT,
            "trusted_composition",
            "read_vulnerability",
            VULNERABILITY_RESOURCE,
            "test",
        ): "allow",
        (
            REMEDIATION_AGENT,
            "api_key",
            "read_vulnerability",
            VULNERABILITY_RESOURCE,
            "test",
        ): "deny",
        (
            OBSERVER_AGENT,
            "trusted_composition",
            "read_vulnerability",
            VULNERABILITY_RESOURCE,
            "test",
        ): "deny",
        (
            REMEDIATION_AGENT,
            "trusted_composition",
            "modify_vulnerability",
            VULNERABILITY_RESOURCE,
            "test",
        ): "deny",
        (
            REMEDIATION_AGENT,
            "trusted_composition",
            "create_remediation_task",
            REMEDIATION_RESOURCE,
            "production",
        ): "require_human_approval",
    }
    return StaticActionAuthorizationPolicy(rules)


def _context(
    caller_id: str = REMEDIATION_AGENT,
    identity_source: CallerIdentitySource = "trusted_composition",
) -> ActionContext:
    return ActionContext(caller_id=caller_id, identity_source=identity_source)


def _vulnerability_action(action: str, environment: str = "test") -> ProposedAction:
    return ProposedAction(
        action=action,
        resource=VULNERABILITY_RESOURCE,
        environment=environment,
    )


def test_action_context_records_default_trusted_identity_source() -> None:
    """Record trusted composition as the default local caller identity provenance."""
    context = _context()

    assert context.caller_id == REMEDIATION_AGENT
    assert context.identity_source == "trusted_composition"


def test_action_context_rejects_unimplemented_authenticated_identity_source() -> None:
    """Reject authentication-like provenance unless the trusted boundary implements it."""
    with pytest.raises(ValidationError, match="identity_source"):
        ActionContext.model_validate(
            {
                "caller_id": REMEDIATION_AGENT,
                "identity_source": "authenticated_principal",
            }
        )


def test_explicitly_allowed_action_is_allowed() -> None:
    """Allow only an exact caller/source/action/resource/environment policy match."""
    decision = _authorizer().authorize(
        _vulnerability_action("read_vulnerability"),
        _context(),
    )

    assert decision.outcome == "allow"
    assert decision.reason == "explicit_allow"


def test_same_caller_and_action_scope_can_differ_by_identity_source() -> None:
    """Treat identity provenance as an independent least-privilege policy dimension."""
    trusted_composition = _authorizer().authorize(
        _vulnerability_action("read_vulnerability"),
        _context(identity_source="trusted_composition"),
    )
    api_key = _authorizer().authorize(
        _vulnerability_action("read_vulnerability"),
        _context(identity_source="api_key"),
    )

    assert trusted_composition.outcome == "allow"
    assert trusted_composition.reason == "explicit_allow"
    assert api_key.outcome == "deny"
    assert api_key.reason == "explicit_deny"


def test_identity_source_without_exact_rule_does_not_inherit_other_source_authority() -> None:
    """Fail closed instead of falling back to a rule for another identity source."""
    rules: dict[ActionAuthorizationRuleKey, AuthorizationOutcome] = {
        (
            REMEDIATION_AGENT,
            "trusted_composition",
            "read_vulnerability",
            VULNERABILITY_RESOURCE,
            "test",
        ): "allow",
    }
    authorizer = StaticActionAuthorizationPolicy(rules)

    decision = authorizer.authorize(
        _vulnerability_action("read_vulnerability"),
        _context(identity_source="api_key"),
    )

    assert decision.outcome == "deny"
    assert decision.reason == "no_matching_rule"


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
    """Deny action escalation even when caller, source, resource, and environment are known."""
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


@pytest.mark.parametrize(
    ("outcome", "reason", "message"),
    [
        ("allow", "explicit_deny", "allow authorization requires explicit_allow"),
        ("allow", "no_matching_rule", "allow authorization requires explicit_allow"),
        ("deny", "explicit_allow", "deny authorization requires"),
        ("deny", "human_approval_required", "deny authorization requires"),
        (
            "require_human_approval",
            "explicit_allow",
            "require_human_approval authorization requires human_approval_required",
        ),
        (
            "require_human_approval",
            "no_matching_rule",
            "require_human_approval authorization requires human_approval_required",
        ),
    ],
)
def test_authorization_decision_rejects_contradictory_outcome_and_reason(
    outcome: AuthorizationOutcome,
    reason: str,
    message: str,
) -> None:
    """Keep persisted caller authorization evidence internally consistent."""
    with pytest.raises(ValidationError, match=message):
        AuthorizationDecision.model_validate({"outcome": outcome, "reason": reason})


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
