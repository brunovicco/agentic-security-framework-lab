"""Tests for deterministic human approver authorization."""

import pytest

from agentic_lab.application.action_approver_authorization import (
    ApproverAuthorizationRuleKey,
    NoActionApproverAuthorizer,
    StaticActionApproverAuthorizationPolicy,
)
from agentic_lab.application.action_authorization import ActionContext, ProposedAction

APPROVER_ID = "soc-reviewer"
CALLER_ID = "remediation-agent"
ACTION = ProposedAction(
    action="create_remediation_task",
    resource="finding:demo-001",
    environment="production",
)
CONTEXT = ActionContext(caller_id=CALLER_ID, identity_source="trusted_composition")
RULE: ApproverAuthorizationRuleKey = (
    APPROVER_ID,
    CALLER_ID,
    "trusted_composition",
    ACTION.action,
    ACTION.resource,
    ACTION.environment,
)


def test_exact_approver_scope_can_be_explicitly_allowed() -> None:
    """Allow only the exact trusted approver/caller/source/action scope named by policy."""
    policy = StaticActionApproverAuthorizationPolicy({RULE: "allow"})

    decision = policy.authorize(APPROVER_ID, ACTION, CONTEXT)

    assert decision.outcome == "allow"
    assert decision.reason == "explicit_allow"


def test_exact_approver_scope_can_be_explicitly_denied() -> None:
    """Preserve an explicit approver deny independently from caller authorization."""
    policy = StaticActionApproverAuthorizationPolicy({RULE: "deny"})

    decision = policy.authorize(APPROVER_ID, ACTION, CONTEXT)

    assert decision.outcome == "deny"
    assert decision.reason == "explicit_deny"


@pytest.mark.parametrize(
    ("approver_id", "context", "action"),
    [
        ("other-reviewer", CONTEXT, ACTION),
        (
            APPROVER_ID,
            ActionContext(caller_id="other-agent", identity_source="trusted_composition"),
            ACTION,
        ),
        (
            APPROVER_ID,
            ActionContext(caller_id=CALLER_ID, identity_source="api_key"),
            ACTION,
        ),
        (
            APPROVER_ID,
            CONTEXT,
            ProposedAction(
                action="delete_remediation_task",
                resource=ACTION.resource,
                environment=ACTION.environment,
            ),
        ),
        (
            APPROVER_ID,
            CONTEXT,
            ProposedAction(
                action=ACTION.action,
                resource="finding:other",
                environment=ACTION.environment,
            ),
        ),
        (
            APPROVER_ID,
            CONTEXT,
            ProposedAction(
                action=ACTION.action,
                resource=ACTION.resource,
                environment="staging",
            ),
        ),
    ],
)
def test_unknown_approver_scope_fails_closed(
    approver_id: str,
    context: ActionContext,
    action: ProposedAction,
) -> None:
    """Deny every dimension mismatch instead of widening approver authority."""
    policy = StaticActionApproverAuthorizationPolicy({RULE: "allow"})

    decision = policy.authorize(approver_id, action, context)

    assert decision.outcome == "deny"
    assert decision.reason == "no_matching_rule"


def test_policy_copies_trusted_rules_at_construction() -> None:
    """Prevent later mutation of the caller-owned mapping from changing approver policy."""
    rules = {RULE: "allow"}
    policy = StaticActionApproverAuthorizationPolicy(rules)
    rules[RULE] = "deny"

    decision = policy.authorize(APPROVER_ID, ACTION, CONTEXT)

    assert decision.outcome == "allow"
    assert decision.reason == "explicit_allow"


def test_missing_approver_policy_fails_closed() -> None:
    """Do not infer approver entitlement merely because trusted approval evidence exists."""
    decision = NoActionApproverAuthorizer().authorize(APPROVER_ID, ACTION, CONTEXT)

    assert decision.outcome == "deny"
    assert decision.reason == "no_matching_rule"
