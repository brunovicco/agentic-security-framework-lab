"""Tests for framework-neutral action authorization."""

from agentic_lab.application.action_authorization import (
    ActionAuthorizer,
    AuthorizationOutcome,
    ProposedAction,
    StaticActionAuthorizationPolicy,
)

VULNERABILITY_RESOURCE = "CVE-2026-DEMO-001"
REMEDIATION_RESOURCE = "finding:demo-001"


def _authorizer() -> ActionAuthorizer:
    rules: dict[tuple[str, str, str], AuthorizationOutcome] = {
        ("read_vulnerability", VULNERABILITY_RESOURCE, "test"): "allow",
        ("modify_vulnerability", VULNERABILITY_RESOURCE, "test"): "deny",
        (
            "create_remediation_task",
            REMEDIATION_RESOURCE,
            "production",
        ): "require_human_approval",
    }
    return StaticActionAuthorizationPolicy(rules)


def _vulnerability_action(action: str, environment: str = "test") -> ProposedAction:
    return ProposedAction(
        action=action,
        resource=VULNERABILITY_RESOURCE,
        environment=environment,
    )


def test_explicitly_allowed_action_is_allowed() -> None:
    """Allow only an exact action/resource/environment policy match."""
    decision = _authorizer().authorize(_vulnerability_action("read_vulnerability"))

    assert decision.outcome == "allow"
    assert decision.reason == "explicit_allow"


def test_explicitly_denied_action_is_denied() -> None:
    """Preserve an explicit deterministic deny decision for an exact scope."""
    decision = _authorizer().authorize(_vulnerability_action("modify_vulnerability"))

    assert decision.outcome == "deny"
    assert decision.reason == "explicit_deny"


def test_approval_gated_scope_requires_human_approval() -> None:
    """Keep an approval-gated production scope distinct from allow."""
    decision = _authorizer().authorize(
        ProposedAction(
            action="create_remediation_task",
            resource=REMEDIATION_RESOURCE,
            environment="production",
        )
    )

    assert decision.outcome == "require_human_approval"
    assert decision.reason == "human_approval_required"


def test_unknown_action_fails_closed() -> None:
    """Deny action escalation even when resource and environment are known."""
    decision = _authorizer().authorize(_vulnerability_action("delete_vulnerability"))

    assert decision.outcome == "deny"
    assert decision.reason == "no_matching_rule"


def test_unauthorized_resource_fails_closed() -> None:
    """Deny resource escalation for an otherwise allowed action."""
    decision = _authorizer().authorize(
        ProposedAction(
            action="read_vulnerability",
            resource="CVE-2026-DEMO-999",
            environment="test",
        )
    )

    assert decision.outcome == "deny"
    assert decision.reason == "no_matching_rule"


def test_unauthorized_environment_fails_closed() -> None:
    """Deny environment escalation for an otherwise allowed action and resource."""
    decision = _authorizer().authorize(
        _vulnerability_action("read_vulnerability", environment="production")
    )

    assert decision.outcome == "deny"
    assert decision.reason == "no_matching_rule"
