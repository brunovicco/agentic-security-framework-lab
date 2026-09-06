"""Provider-free adversarial integration tests for governed agent actions."""

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from agentic_lab.adapters.fixtures.action_approvals import InMemoryActionApprovalProvider
from agentic_lab.adapters.fixtures.finding_actions import (
    InMemoryFindingAcknowledgementExecutor,
)
from agentic_lab.application.action_approval import HumanApprovalEvidence
from agentic_lab.application.action_approver_authorization import (
    StaticActionApproverAuthorizationPolicy,
)
from agentic_lab.application.action_authorization import (
    ActionAuthorizationRuleKey,
    ActionContext,
    AuthorizationDecision,
    AuthorizationOutcome,
    CallerIdentitySource,
    ProposedAction,
    StaticActionAuthorizationPolicy,
)
from agentic_lab.application.action_runtime import GovernedActionRuntime

FINDING_RESOURCE = "finding:demo-001"
OTHER_FINDING_RESOURCE = "finding:demo-999"
REMEDIATION_AGENT = "remediation-agent"
OBSERVER_AGENT = "observer-agent"
APPROVED_AT = datetime(2026, 9, 5, 20, 0, tzinfo=UTC)
EXPIRES_AT = APPROVED_AT + timedelta(minutes=15)
VALID_NOW = APPROVED_AT + timedelta(minutes=5)


class FixedApprovalClock:
    """Return deterministic trusted time for adversarial approval checks."""

    def __init__(self, current_time: datetime) -> None:
        self._current_time = current_time

    def now(self) -> datetime:
        """Return the configured timezone-aware current time."""
        return self._current_time


class CountingActionAuthorizer:
    """Count authorization decisions independently from tool executions."""

    def __init__(self, delegate: StaticActionAuthorizationPolicy) -> None:
        self._delegate = delegate
        self.authorization_calls = 0

    def authorize(
        self,
        proposed_action: ProposedAction,
        context: ActionContext,
    ) -> AuthorizationDecision:
        """Record one decision request before delegating to deterministic policy."""
        self.authorization_calls += 1
        return self._delegate.authorize(proposed_action, context)


def _policy() -> StaticActionAuthorizationPolicy:
    rules: dict[ActionAuthorizationRuleKey, AuthorizationOutcome] = {
        (
            OBSERVER_AGENT,
            "trusted_composition",
            "read_finding",
            FINDING_RESOURCE,
            "test",
        ): "allow",
        (
            REMEDIATION_AGENT,
            "trusted_composition",
            "acknowledge_finding",
            FINDING_RESOURCE,
            "test",
        ): "allow",
        (
            REMEDIATION_AGENT,
            "trusted_composition",
            "acknowledge_finding",
            FINDING_RESOURCE,
            "staging",
        ): "deny",
        (
            REMEDIATION_AGENT,
            "trusted_composition",
            "acknowledge_finding",
            FINDING_RESOURCE,
            "production",
        ): "require_human_approval",
    }
    return StaticActionAuthorizationPolicy(rules)


def _approver_authorizer() -> StaticActionApproverAuthorizationPolicy:
    return StaticActionApproverAuthorizationPolicy(
        {
            (
                "soc-reviewer",
                REMEDIATION_AGENT,
                "trusted_composition",
                "acknowledge_finding",
                FINDING_RESOURCE,
                "production",
            ): "allow"
        }
    )


def _runtime(
    executor: InMemoryFindingAcknowledgementExecutor,
) -> GovernedActionRuntime:
    return GovernedActionRuntime(authorizer=_policy(), executor=executor)


def _context(
    caller_id: str = REMEDIATION_AGENT,
    identity_source: CallerIdentitySource = "trusted_composition",
) -> ActionContext:
    return ActionContext(caller_id=caller_id, identity_source=identity_source)


def _action(
    *,
    action: str = "acknowledge_finding",
    resource: str = FINDING_RESOURCE,
    environment: str = "test",
) -> ProposedAction:
    return ProposedAction(
        action=action,
        resource=resource,
        environment=environment,
    )


def test_tool_escalation_from_read_only_caller_is_denied() -> None:
    """Do not turn narrow read capability into mutable tool authority."""
    executor = InMemoryFindingAcknowledgementExecutor([FINDING_RESOURCE])

    evidence = _runtime(executor).execute(
        _action(),
        _context(OBSERVER_AGENT),
    )

    assert evidence.authorization.outcome == "deny"
    assert evidence.authorization.reason == "no_matching_rule"
    assert evidence.execution_occurred is False
    assert executor.is_acknowledged(FINDING_RESOURCE) is False
    assert executor.execution_count == 0


def test_identity_source_substitution_does_not_inherit_composition_authority() -> None:
    """Deny the same caller scope when identity provenance does not match its policy rule."""
    executor = InMemoryFindingAcknowledgementExecutor([FINDING_RESOURCE])

    evidence = _runtime(executor).execute(
        _action(),
        _context(identity_source="api_key"),
    )

    assert evidence.context.caller_id == REMEDIATION_AGENT
    assert evidence.context.identity_source == "api_key"
    assert evidence.authorization.outcome == "deny"
    assert evidence.authorization.reason == "no_matching_rule"
    assert evidence.execution_occurred is False
    assert executor.execution_count == 0
    assert executor.is_acknowledged(FINDING_RESOURCE) is False


def test_wrong_identity_source_cannot_consume_correct_source_approval() -> None:
    """Keep approval authority available after an approval-gated cross-source attempt."""
    proposed_action = _action(environment="production")
    trusted_context = _context(identity_source="trusted_composition")
    api_key_context = _context(identity_source="api_key")
    rules: dict[ActionAuthorizationRuleKey, AuthorizationOutcome] = {
        (
            REMEDIATION_AGENT,
            "trusted_composition",
            proposed_action.action,
            proposed_action.resource,
            proposed_action.environment,
        ): "require_human_approval",
        (
            REMEDIATION_AGENT,
            "api_key",
            proposed_action.action,
            proposed_action.resource,
            proposed_action.environment,
        ): "require_human_approval",
    }
    approval = HumanApprovalEvidence(
        approval_id="approval-source-isolation-001",
        approver_id="soc-reviewer",
        proposed_action=proposed_action,
        context=trusted_context,
        approved_at=APPROVED_AT,
        expires_at=EXPIRES_AT,
    )
    executor = InMemoryFindingAcknowledgementExecutor([FINDING_RESOURCE])
    runtime = GovernedActionRuntime(
        authorizer=StaticActionAuthorizationPolicy(rules),
        executor=executor,
        approval_provider=InMemoryActionApprovalProvider([approval]),
        approval_clock=FixedApprovalClock(VALID_NOW),
        approver_authorizer=_approver_authorizer(),
    )

    wrong_source = runtime.execute(proposed_action, api_key_context)
    correct_source = runtime.execute(proposed_action, trusted_context)

    assert wrong_source.authorization.outcome == "require_human_approval"
    assert wrong_source.approval_status == "missing"
    assert wrong_source.execution_occurred is False
    assert correct_source.authorization.outcome == "require_human_approval"
    assert correct_source.approval_status == "validated"
    assert correct_source.human_approval == approval
    assert correct_source.execution_occurred is True
    assert executor.execution_count == 1
    assert executor.is_acknowledged(FINDING_RESOURCE) is True


def test_resource_and_environment_escalation_remain_blocked() -> None:
    """Evaluate the actual requested scope instead of the nearest permitted scope."""
    executor = InMemoryFindingAcknowledgementExecutor([FINDING_RESOURCE])
    runtime = _runtime(executor)

    resource_escalation = runtime.execute(
        _action(resource=OTHER_FINDING_RESOURCE),
        _context(),
    )
    production_escalation = runtime.execute(
        _action(environment="production"),
        _context(),
    )

    assert resource_escalation.authorization.outcome == "deny"
    assert resource_escalation.authorization.reason == "no_matching_rule"
    assert resource_escalation.execution_occurred is False
    assert production_escalation.authorization.outcome == "require_human_approval"
    assert production_escalation.execution_occurred is False
    assert executor.is_acknowledged(FINDING_RESOURCE) is False
    assert executor.execution_count == 0


def test_untrusted_proposal_cannot_spoof_privileged_caller_identity() -> None:
    """Reject caller identity embedded in the model-adjacent proposal payload."""
    with pytest.raises(ValidationError, match="caller_id"):
        ProposedAction.model_validate(
            {
                "action": "acknowledge_finding",
                "resource": FINDING_RESOURCE,
                "environment": "test",
                "caller_id": REMEDIATION_AGENT,
            }
        )


def test_fake_approval_in_proposal_cannot_become_authority() -> None:
    """Reject approval-like model content rather than synthesizing trusted HITL state."""
    with pytest.raises(ValidationError, match="approved_by"):
        ProposedAction.model_validate(
            {
                "action": "acknowledge_finding",
                "resource": FINDING_RESOURCE,
                "environment": "production",
                "approved_by": "SOC Manager",
            }
        )


def test_retry_after_deny_does_not_accumulate_authority() -> None:
    """Keep repeated denied attempts independent from execution permission."""
    executor = InMemoryFindingAcknowledgementExecutor([FINDING_RESOURCE])
    authorizer = CountingActionAuthorizer(_policy())
    runtime = GovernedActionRuntime(authorizer=authorizer, executor=executor)
    denied_action = _action(environment="staging")

    first = runtime.execute(denied_action, _context())
    second = runtime.execute(denied_action, _context())

    assert first.authorization.outcome == "deny"
    assert second.authorization.outcome == "deny"
    assert first.execution_occurred is False
    assert second.execution_occurred is False
    assert authorizer.authorization_calls == 2
    assert executor.execution_count == 0
    assert executor.is_acknowledged(FINDING_RESOURCE) is False


def test_consumed_human_approval_cannot_be_replayed() -> None:
    """Require a fresh trusted approval for a repeated mutable production action."""
    executor = InMemoryFindingAcknowledgementExecutor([FINDING_RESOURCE])
    proposed_action = _action(environment="production")
    context = _context()
    approval = HumanApprovalEvidence(
        approval_id="approval-replay-001",
        approver_id="soc-reviewer",
        proposed_action=proposed_action,
        context=context,
        approved_at=APPROVED_AT,
        expires_at=EXPIRES_AT,
    )
    runtime = GovernedActionRuntime(
        authorizer=_policy(),
        executor=executor,
        approval_provider=InMemoryActionApprovalProvider([approval]),
        approval_clock=FixedApprovalClock(VALID_NOW),
        approver_authorizer=_approver_authorizer(),
    )

    first = runtime.execute(proposed_action, context)
    replay = runtime.execute(proposed_action, context)

    assert first.authorization.outcome == "require_human_approval"
    assert first.approval_status == "validated"
    assert first.execution_occurred is True
    assert replay.authorization.outcome == "require_human_approval"
    assert replay.approval_status == "missing"
    assert replay.execution_occurred is False
    assert executor.execution_count == 1
    assert executor.is_acknowledged(FINDING_RESOURCE) is True


def test_stale_unused_human_approval_cannot_authorize_late_mutation() -> None:
    """Treat old unconsumed human intent as expired authority, then consume it."""
    executor = InMemoryFindingAcknowledgementExecutor([FINDING_RESOURCE])
    proposed_action = _action(environment="production")
    context = _context()
    approval = HumanApprovalEvidence(
        approval_id="approval-stale-001",
        approver_id="soc-reviewer",
        proposed_action=proposed_action,
        context=context,
        approved_at=APPROVED_AT,
        expires_at=EXPIRES_AT,
    )
    runtime = GovernedActionRuntime(
        authorizer=_policy(),
        executor=executor,
        approval_provider=InMemoryActionApprovalProvider([approval]),
        approval_clock=FixedApprovalClock(EXPIRES_AT),
        approver_authorizer=_approver_authorizer(),
    )

    stale = runtime.execute(proposed_action, context)
    retry = runtime.execute(proposed_action, context)

    assert stale.authorization.outcome == "require_human_approval"
    assert stale.approval_status == "expired"
    assert stale.human_approval == approval
    assert stale.execution_occurred is False
    assert retry.approval_status == "missing"
    assert retry.execution_occurred is False
    assert executor.execution_count == 0
    assert executor.is_acknowledged(FINDING_RESOURCE) is False


def test_revoked_unused_human_approval_cannot_authorize_mutation() -> None:
    """Prevent a valid but explicitly revoked capability from causing a side effect."""
    executor = InMemoryFindingAcknowledgementExecutor([FINDING_RESOURCE])
    proposed_action = _action(environment="production")
    context = _context()
    approval = HumanApprovalEvidence(
        approval_id="approval-revoked-001",
        approver_id="soc-reviewer",
        proposed_action=proposed_action,
        context=context,
        approved_at=APPROVED_AT,
        expires_at=EXPIRES_AT,
    )
    provider = InMemoryActionApprovalProvider([approval])
    assert provider.revoke_approval(approval.approval_id) is True
    runtime = GovernedActionRuntime(
        authorizer=_policy(),
        executor=executor,
        approval_provider=provider,
        approval_clock=FixedApprovalClock(VALID_NOW),
        approver_authorizer=_approver_authorizer(),
    )

    revoked = runtime.execute(proposed_action, context)
    retry = runtime.execute(proposed_action, context)

    assert revoked.authorization.outcome == "require_human_approval"
    assert revoked.approval_status == "revoked"
    assert revoked.human_approval == approval
    assert revoked.execution_occurred is False
    assert retry.approval_status == "missing"
    assert retry.execution_occurred is False
    assert executor.execution_count == 0
    assert executor.is_acknowledged(FINDING_RESOURCE) is False


def test_unentitled_human_approver_cannot_authorize_mutation() -> None:
    """Reject exact live approval when the trusted approver lacks exact entitlement."""
    executor = InMemoryFindingAcknowledgementExecutor([FINDING_RESOURCE])
    proposed_action = _action(environment="production")
    context = _context()
    approval = HumanApprovalEvidence(
        approval_id="approval-unentitled-001",
        approver_id="unprivileged-reviewer",
        proposed_action=proposed_action,
        context=context,
        approved_at=APPROVED_AT,
        expires_at=EXPIRES_AT,
    )
    runtime = GovernedActionRuntime(
        authorizer=_policy(),
        executor=executor,
        approval_provider=InMemoryActionApprovalProvider([approval]),
        approval_clock=FixedApprovalClock(VALID_NOW),
        approver_authorizer=_approver_authorizer(),
    )

    first = runtime.execute(proposed_action, context)
    retry = runtime.execute(proposed_action, context)

    assert first.authorization.outcome == "require_human_approval"
    assert first.approval_status == "unauthorized_approver"
    assert first.approver_authorization is not None
    assert first.approver_authorization.outcome == "deny"
    assert first.approver_authorization.reason == "no_matching_rule"
    assert first.execution_occurred is False
    assert retry.approval_status == "missing"
    assert executor.execution_count == 0
    assert executor.is_acknowledged(FINDING_RESOURCE) is False


def test_tool_substitution_is_authorized_as_the_actual_proposed_action() -> None:
    """Deny a substituted broader operation despite an allowed nearby capability."""
    executor = InMemoryFindingAcknowledgementExecutor([FINDING_RESOURCE])

    evidence = _runtime(executor).execute(
        _action(action="delete_finding"),
        _context(),
    )

    assert evidence.authorization.outcome == "deny"
    assert evidence.authorization.reason == "no_matching_rule"
    assert evidence.execution_occurred is False
    assert executor.execution_count == 0
    assert executor.is_acknowledged(FINDING_RESOURCE) is False


def test_unsafe_proposal_does_not_imply_unsafe_side_effect() -> None:
    """Contain an unsafe proposal without claiming anything about model quality."""
    executor = InMemoryFindingAcknowledgementExecutor([FINDING_RESOURCE])

    evidence = _runtime(executor).execute(
        _action(environment="production"),
        _context(),
    )

    assert evidence.authorization.outcome == "require_human_approval"
    assert evidence.execution_occurred is False
    assert executor.execution_count == 0
    assert executor.is_acknowledged(FINDING_RESOURCE) is False
