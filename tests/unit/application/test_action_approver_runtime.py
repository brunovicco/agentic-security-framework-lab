"""Tests for independent human approver authorization in governed runtime execution."""

from datetime import UTC, datetime, timedelta
from typing import Literal

import pytest

from agentic_lab.application.action_approval import (
    ApprovalClaim,
    ApprovalClaimStatus,
    HumanApprovalEvidence,
)
from agentic_lab.application.action_approver_authorization import (
    ApproverAuthorizationDecision,
    StaticActionApproverAuthorizationPolicy,
)
from agentic_lab.application.action_authorization import (
    ActionAuthorizationRuleKey,
    ActionContext,
    AuthorizationOutcome,
    ProposedAction,
    StaticActionAuthorizationPolicy,
)
from agentic_lab.application.action_runtime import ActionExecutionEvidence, GovernedActionRuntime

CALLER_ID = "remediation-agent"
APPROVER_ID = "soc-reviewer"
RESOURCE = "finding:demo-001"
APPROVED_AT = datetime(2026, 9, 5, 20, 0, tzinfo=UTC)
VALID_NOW = APPROVED_AT + timedelta(minutes=5)
EXPIRES_AT = APPROVED_AT + timedelta(minutes=15)


class RecordingExecutor:
    """Record mutable executions that cross every governed boundary."""

    def __init__(self) -> None:
        self.actions: list[ProposedAction] = []

    def execute(self, proposed_action: ProposedAction) -> None:
        self.actions.append(proposed_action)


class OneShotApprovalProvider:
    """Return one configured approval claim and then fail closed as missing."""

    def __init__(
        self,
        approval: HumanApprovalEvidence | None,
        *,
        status: Literal["claimed", "revoked"] = "claimed",
    ) -> None:
        self._approval = approval
        self._status: ApprovalClaimStatus = status
        self.calls = 0

    def claim_approval(
        self,
        proposed_action: ProposedAction,
        context: ActionContext,
    ) -> ApprovalClaim:
        del proposed_action, context
        self.calls += 1
        approval = self._approval
        self._approval = None
        if approval is None:
            return ApprovalClaim(status="missing")
        return ApprovalClaim(status=self._status, approval=approval)


class FixedClock:
    """Return deterministic trusted time while recording access."""

    def __init__(self, now: datetime) -> None:
        self._now = now
        self.calls = 0

    def now(self) -> datetime:
        self.calls += 1
        return self._now


class UnexpectedClock:
    """Fail if time is consulted before an earlier security boundary completes."""

    def now(self) -> datetime:
        raise AssertionError("approval clock must not be consulted")


class UnexpectedApproverAuthorizer:
    """Fail if approver entitlement is consulted on a path where HITL is irrelevant."""

    def authorize(
        self,
        approver_id: str,
        proposed_action: ProposedAction,
        context: ActionContext,
    ) -> ApproverAuthorizationDecision:
        del approver_id, proposed_action, context
        raise AssertionError("approver authorization must not be consulted")


def _action(
    *,
    action: str = "create_remediation_task",
    resource: str = RESOURCE,
    environment: str = "production",
) -> ProposedAction:
    return ProposedAction(action=action, resource=resource, environment=environment)


def _context(
    identity_source: Literal["trusted_composition", "api_key"] = "trusted_composition",
) -> ActionContext:
    return ActionContext(caller_id=CALLER_ID, identity_source=identity_source)


def _caller_authorizer() -> StaticActionAuthorizationPolicy:
    rules: dict[ActionAuthorizationRuleKey, AuthorizationOutcome] = {
        (
            CALLER_ID,
            "trusted_composition",
            "create_remediation_task",
            RESOURCE,
            "production",
        ): "require_human_approval",
        (
            CALLER_ID,
            "api_key",
            "create_remediation_task",
            RESOURCE,
            "production",
        ): "require_human_approval",
        (
            CALLER_ID,
            "trusted_composition",
            "read_finding",
            RESOURCE,
            "test",
        ): "allow",
        (
            CALLER_ID,
            "trusted_composition",
            "delete_finding",
            RESOURCE,
            "production",
        ): "deny",
    }
    return StaticActionAuthorizationPolicy(rules)


def _approval(
    proposed_action: ProposedAction,
    context: ActionContext,
    *,
    approver_id: str = APPROVER_ID,
) -> HumanApprovalEvidence:
    return HumanApprovalEvidence(
        approval_id="approval-001",
        approver_id=approver_id,
        proposed_action=proposed_action,
        context=context,
        approved_at=APPROVED_AT,
        expires_at=EXPIRES_AT,
    )


def _approver_policy(
    *,
    outcome: Literal["allow", "deny"] = "allow",
    identity_source: Literal["trusted_composition", "api_key"] = "trusted_composition",
) -> StaticActionApproverAuthorizationPolicy:
    return StaticActionApproverAuthorizationPolicy(
        {
            (
                APPROVER_ID,
                CALLER_ID,
                identity_source,
                "create_remediation_task",
                RESOURCE,
                "production",
            ): outcome
        }
    )


def test_default_approver_authorizer_fails_closed_and_consumes_claim() -> None:
    """Trusted approval evidence alone must not imply approver entitlement."""
    action = _action()
    context = _context()
    approval = _approval(action, context)
    provider = OneShotApprovalProvider(approval)
    executor = RecordingExecutor()
    runtime = GovernedActionRuntime(
        authorizer=_caller_authorizer(),
        executor=executor,
        approval_provider=provider,
        approval_clock=UnexpectedClock(),
    )

    first = runtime.execute(action, context)
    second = runtime.execute(action, context)

    assert first.approval_status == "unauthorized_approver"
    assert first.human_approval == approval
    assert first.approver_authorization is not None
    assert first.approver_authorization.outcome == "deny"
    assert first.approver_authorization.reason == "no_matching_rule"
    assert first.execution_occurred is False
    assert second.approval_status == "missing"
    assert second.approver_authorization is None
    assert executor.actions == []
    assert provider.calls == 2


def test_explicitly_authorized_approver_can_release_live_approval() -> None:
    """Require caller policy, approval evidence, approver policy, and time before execution."""
    action = _action()
    context = _context()
    approval = _approval(action, context)
    provider = OneShotApprovalProvider(approval)
    clock = FixedClock(VALID_NOW)
    executor = RecordingExecutor()
    runtime = GovernedActionRuntime(
        authorizer=_caller_authorizer(),
        executor=executor,
        approval_provider=provider,
        approval_clock=clock,
        approver_authorizer=_approver_policy(),
    )

    evidence = runtime.execute(action, context)

    assert evidence.authorization.outcome == "require_human_approval"
    assert evidence.approval_status == "validated"
    assert evidence.human_approval == approval
    assert evidence.approver_authorization is not None
    assert evidence.approver_authorization.outcome == "allow"
    assert evidence.approver_authorization.reason == "explicit_allow"
    assert evidence.execution_occurred is True
    assert executor.actions == [action]
    assert clock.calls == 1


def test_explicit_approver_deny_is_terminal_before_time_and_execution() -> None:
    """Keep caller authorization independent from an explicit human entitlement deny."""
    action = _action()
    context = _context()
    approval = _approval(action, context)
    executor = RecordingExecutor()
    runtime = GovernedActionRuntime(
        authorizer=_caller_authorizer(),
        executor=executor,
        approval_provider=OneShotApprovalProvider(approval),
        approval_clock=UnexpectedClock(),
        approver_authorizer=_approver_policy(outcome="deny"),
    )

    evidence = runtime.execute(action, context)

    assert evidence.authorization.outcome == "require_human_approval"
    assert evidence.approval_status == "unauthorized_approver"
    assert evidence.approver_authorization is not None
    assert evidence.approver_authorization.outcome == "deny"
    assert evidence.approver_authorization.reason == "explicit_deny"
    assert evidence.execution_occurred is False
    assert executor.actions == []


def test_approver_entitlement_is_isolated_by_caller_identity_source() -> None:
    """Do not reuse trusted-composition approver authority for the same API-key caller id."""
    action = _action()
    context = _context("api_key")
    approval = _approval(action, context)
    executor = RecordingExecutor()
    runtime = GovernedActionRuntime(
        authorizer=_caller_authorizer(),
        executor=executor,
        approval_provider=OneShotApprovalProvider(approval),
        approval_clock=UnexpectedClock(),
        approver_authorizer=_approver_policy(identity_source="trusted_composition"),
    )

    evidence = runtime.execute(action, context)

    assert evidence.authorization.outcome == "require_human_approval"
    assert evidence.approval_status == "unauthorized_approver"
    assert evidence.approver_authorization is not None
    assert evidence.approver_authorization.reason == "no_matching_rule"
    assert evidence.execution_occurred is False
    assert executor.actions == []


def test_caller_allow_does_not_consult_approver_authorization() -> None:
    """Do not introduce a human boundary when caller policy permits direct execution."""
    action = _action(action="read_finding", environment="test")
    executor = RecordingExecutor()
    runtime = GovernedActionRuntime(
        authorizer=_caller_authorizer(),
        executor=executor,
        approver_authorizer=UnexpectedApproverAuthorizer(),
    )

    evidence = runtime.execute(action, _context())

    assert evidence.authorization.outcome == "allow"
    assert evidence.approval_status == "not_applicable"
    assert evidence.approver_authorization is None
    assert evidence.execution_occurred is True
    assert executor.actions == [action]


def test_caller_deny_does_not_consult_approver_authorization() -> None:
    """Keep caller deny terminal before any human entitlement decision."""
    action = _action(action="delete_finding")
    executor = RecordingExecutor()
    runtime = GovernedActionRuntime(
        authorizer=_caller_authorizer(),
        executor=executor,
        approver_authorizer=UnexpectedApproverAuthorizer(),
    )

    evidence = runtime.execute(action, _context())

    assert evidence.authorization.outcome == "deny"
    assert evidence.approval_status == "not_applicable"
    assert evidence.approver_authorization is None
    assert evidence.execution_occurred is False
    assert executor.actions == []


def test_missing_approval_does_not_consult_approver_authorization() -> None:
    """Do not ask who may approve when no approval capability was claimed."""
    executor = RecordingExecutor()
    runtime = GovernedActionRuntime(
        authorizer=_caller_authorizer(),
        executor=executor,
        approval_provider=OneShotApprovalProvider(None),
        approver_authorizer=UnexpectedApproverAuthorizer(),
    )

    evidence = runtime.execute(_action(), _context())

    assert evidence.approval_status == "missing"
    assert evidence.approver_authorization is None
    assert evidence.execution_occurred is False
    assert executor.actions == []


def test_invalid_approval_binding_does_not_consult_approver_authorization() -> None:
    """Reject wrong action scope before interpreting the approver identity as authority."""
    action = _action()
    context = _context()
    approval = _approval(_action(resource="finding:other"), context)
    executor = RecordingExecutor()
    runtime = GovernedActionRuntime(
        authorizer=_caller_authorizer(),
        executor=executor,
        approval_provider=OneShotApprovalProvider(approval),
        approval_clock=UnexpectedClock(),
        approver_authorizer=UnexpectedApproverAuthorizer(),
    )

    evidence = runtime.execute(action, context)

    assert evidence.approval_status == "invalid"
    assert evidence.approver_authorization is None
    assert evidence.execution_occurred is False
    assert executor.actions == []


def test_revoked_approval_does_not_consult_approver_authorization() -> None:
    """Keep revocation terminal before approver entitlement or freshness checks."""
    action = _action()
    context = _context()
    approval = _approval(action, context)
    executor = RecordingExecutor()
    runtime = GovernedActionRuntime(
        authorizer=_caller_authorizer(),
        executor=executor,
        approval_provider=OneShotApprovalProvider(approval, status="revoked"),
        approval_clock=UnexpectedClock(),
        approver_authorizer=UnexpectedApproverAuthorizer(),
    )

    evidence = runtime.execute(action, context)

    assert evidence.approval_status == "revoked"
    assert evidence.approver_authorization is None
    assert evidence.execution_occurred is False
    assert executor.actions == []


def test_unauthorized_status_requires_deny_approver_decision() -> None:
    """Reject evidence that calls an explicitly allowed approver unauthorized."""
    action = _action()
    context = _context()
    with pytest.raises(ValueError, match="requires a deny decision"):
        ActionExecutionEvidence(
            proposed_action=action,
            context=context,
            authorization=_caller_authorizer().authorize(action, context),
            approval_status="unauthorized_approver",
            human_approval=_approval(action, context),
            approver_authorization=ApproverAuthorizationDecision(
                outcome="allow",
                reason="explicit_allow",
            ),
            execution_occurred=False,
        )


def test_validated_status_requires_allow_approver_decision() -> None:
    """Reject evidence that records validated approval after an approver deny."""
    action = _action()
    context = _context()
    with pytest.raises(ValueError, match="validated approval status requires an allow decision"):
        ActionExecutionEvidence(
            proposed_action=action,
            context=context,
            authorization=_caller_authorizer().authorize(action, context),
            approval_status="validated",
            human_approval=_approval(action, context),
            approver_authorization=ApproverAuthorizationDecision(
                outcome="deny",
                reason="explicit_deny",
            ),
            execution_occurred=False,
        )


def test_pre_approver_status_cannot_carry_approver_decision() -> None:
    """Keep missing approval evidence separate from approver authorization facts."""
    action = _action()
    context = _context()
    with pytest.raises(ValueError, match="missing approval status cannot carry"):
        ActionExecutionEvidence(
            proposed_action=action,
            context=context,
            authorization=_caller_authorizer().authorize(action, context),
            approval_status="missing",
            human_approval=None,
            approver_authorization=ApproverAuthorizationDecision(
                outcome="deny",
                reason="no_matching_rule",
            ),
            execution_occurred=False,
        )
