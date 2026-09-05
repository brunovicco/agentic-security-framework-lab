"""Tests for framework-neutral governed action runtime enforcement."""

from datetime import UTC, datetime, timedelta
from typing import Literal

import pytest

from agentic_lab.application.action_approval import ApprovalClaim, HumanApprovalEvidence
from agentic_lab.application.action_authorization import (
    ActionAuthorizationRuleKey,
    ActionAuthorizer,
    ActionContext,
    AuthorizationDecision,
    AuthorizationOutcome,
    ProposedAction,
    StaticActionAuthorizationPolicy,
)
from agentic_lab.application.action_runtime import GovernedActionRuntime

VULNERABILITY_RESOURCE = "CVE-2026-DEMO-001"
REMEDIATION_RESOURCE = "finding:demo-001"
REMEDIATION_AGENT = "remediation-agent"
APPROVED_AT = datetime(2026, 9, 5, 20, 0, tzinfo=UTC)
EXPIRES_AT = APPROVED_AT + timedelta(minutes=15)
VALID_NOW = APPROVED_AT + timedelta(minutes=5)


class RecordingActionExecutor:
    """Record actions that cross the runtime enforcement boundary."""

    def __init__(self) -> None:
        self.actions: list[ProposedAction] = []

    def execute(self, proposed_action: ProposedAction) -> None:
        """Record one executed action without performing an external side effect."""
        self.actions.append(proposed_action)


class FailingActionExecutor:
    """Fail after crossing the runtime boundary while recording call count."""

    def __init__(self) -> None:
        self.calls = 0

    def execute(self, proposed_action: ProposedAction) -> None:
        """Record one attempted side effect and fail deterministically."""
        self.calls += 1
        raise RuntimeError(f"executor failed for {proposed_action.action}")


class RecordingApprovalProvider:
    """Return one explicit approval claim while recording trusted attempts."""

    def __init__(
        self,
        approval: HumanApprovalEvidence | None,
        *,
        claim_status: Literal["claimed", "revoked"] = "claimed",
    ) -> None:
        self._approval = approval
        self._claim_status = claim_status
        self.claim_calls = 0

    def claim_approval(
        self,
        proposed_action: ProposedAction,
        context: ActionContext,
    ) -> ApprovalClaim:
        """Consume configured evidence without silently rebinding its scope."""
        self.claim_calls += 1
        approval = self._approval
        self._approval = None
        if approval is None:
            return ApprovalClaim(status="missing")
        return ApprovalClaim(status=self._claim_status, approval=approval)


class FixedApprovalClock:
    """Return one deterministic current time for approval freshness tests."""

    def __init__(self, current_time: datetime) -> None:
        self._current_time = current_time
        self.calls = 0

    def now(self) -> datetime:
        """Return the configured time while recording runtime clock access."""
        self.calls += 1
        return self._current_time


class UnexpectedApprovalClock:
    """Fail if a runtime path consults approval time when HITL is irrelevant."""

    def now(self) -> datetime:
        """Reject unexpected clock access."""
        raise AssertionError("approval clock must not be consulted on this path")


class FailingAuthorizer:
    """Represent an authorization decision point that cannot produce a decision."""

    def authorize(
        self,
        proposed_action: ProposedAction,
        context: ActionContext,
    ) -> AuthorizationDecision:
        """Fail before any authorization decision can be established."""
        raise RuntimeError(
            f"authorization unavailable for {context.caller_id}:{proposed_action.action}"
        )


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


def _context(caller_id: str = REMEDIATION_AGENT) -> ActionContext:
    return ActionContext(caller_id=caller_id)


def _vulnerability_action(action: str, environment: str = "test") -> ProposedAction:
    return ProposedAction(
        action=action,
        resource=VULNERABILITY_RESOURCE,
        environment=environment,
    )


def _remediation_action(resource: str = REMEDIATION_RESOURCE) -> ProposedAction:
    return ProposedAction(
        action="create_remediation_task",
        resource=resource,
        environment="production",
    )


def _approval(
    proposed_action: ProposedAction,
    context: ActionContext,
    *,
    approved_at: datetime = APPROVED_AT,
    expires_at: datetime = EXPIRES_AT,
) -> HumanApprovalEvidence:
    return HumanApprovalEvidence(
        approval_id="approval-001",
        approver_id="soc-reviewer",
        proposed_action=proposed_action,
        context=context,
        approved_at=approved_at,
        expires_at=expires_at,
    )


def test_allowed_action_reaches_executor_without_approval_claim_or_clock() -> None:
    """Execute explicit allow without consuming or timing irrelevant HITL evidence."""
    executor = RecordingActionExecutor()
    approval_provider = RecordingApprovalProvider(None)
    runtime = GovernedActionRuntime(
        authorizer=_authorizer(),
        executor=executor,
        approval_provider=approval_provider,
        approval_clock=UnexpectedApprovalClock(),
    )
    proposed_action = _vulnerability_action("read_vulnerability")
    context = _context()

    evidence = runtime.execute(proposed_action, context)

    assert executor.actions == [proposed_action]
    assert evidence.proposed_action == proposed_action
    assert evidence.context == context
    assert evidence.context.identity_source == "trusted_composition"
    assert evidence.authorization.outcome == "allow"
    assert evidence.approval_status == "not_applicable"
    assert evidence.human_approval is None
    assert evidence.execution_occurred is True
    assert approval_provider.claim_calls == 0


def test_unknown_caller_never_reaches_executor() -> None:
    """Block a valid action scope when trusted caller identity has no matching rule."""
    executor = RecordingActionExecutor()
    runtime = GovernedActionRuntime(authorizer=_authorizer(), executor=executor)

    evidence = runtime.execute(
        _vulnerability_action("read_vulnerability"),
        _context("unknown-agent"),
    )

    assert executor.actions == []
    assert evidence.context.caller_id == "unknown-agent"
    assert evidence.authorization.outcome == "deny"
    assert evidence.authorization.reason == "no_matching_rule"
    assert evidence.approval_status == "not_applicable"
    assert evidence.execution_occurred is False


def test_denied_action_cannot_override_or_consume_approval_or_clock() -> None:
    """Keep explicit deny terminal without consuming or timing approval capacity."""
    executor = RecordingActionExecutor()
    denied_action = _vulnerability_action("modify_vulnerability")
    context = _context()
    approval_provider = RecordingApprovalProvider(_approval(denied_action, context))
    runtime = GovernedActionRuntime(
        authorizer=_authorizer(),
        executor=executor,
        approval_provider=approval_provider,
        approval_clock=UnexpectedApprovalClock(),
    )

    evidence = runtime.execute(denied_action, context)

    assert executor.actions == []
    assert evidence.authorization.outcome == "deny"
    assert evidence.authorization.reason == "explicit_deny"
    assert evidence.approval_status == "not_applicable"
    assert evidence.human_approval is None
    assert evidence.execution_occurred is False
    assert approval_provider.claim_calls == 0


def test_approval_required_action_is_blocked_when_approval_is_missing() -> None:
    """Block approval-required execution when the trusted HITL source has no evidence."""
    executor = RecordingActionExecutor()
    runtime = GovernedActionRuntime(authorizer=_authorizer(), executor=executor)

    evidence = runtime.execute(_remediation_action(), _context())

    assert executor.actions == []
    assert evidence.authorization.outcome == "require_human_approval"
    assert evidence.approval_status == "missing"
    assert evidence.human_approval is None
    assert evidence.execution_occurred is False


def test_revoked_approval_is_consumed_and_blocked_before_clock() -> None:
    """Block revoked authority before trusted time or mutable execution is relevant."""
    executor = RecordingActionExecutor()
    proposed_action = _remediation_action()
    context = _context()
    approval = _approval(proposed_action, context)
    approval_provider = RecordingApprovalProvider(approval, claim_status="revoked")
    runtime = GovernedActionRuntime(
        authorizer=_authorizer(),
        executor=executor,
        approval_provider=approval_provider,
        approval_clock=UnexpectedApprovalClock(),
    )

    first = runtime.execute(proposed_action, context)
    second = runtime.execute(proposed_action, context)

    assert first.authorization.outcome == "require_human_approval"
    assert first.approval_status == "revoked"
    assert first.human_approval == approval
    assert first.execution_occurred is False
    assert second.approval_status == "missing"
    assert second.human_approval is None
    assert second.execution_occurred is False
    assert executor.actions == []
    assert approval_provider.claim_calls == 2


def test_approval_is_valid_at_inclusive_approved_at_boundary() -> None:
    """Accept exact-scope approval starting at its timezone-aware issuance instant."""
    executor = RecordingActionExecutor()
    proposed_action = _remediation_action()
    context = _context()
    approval = _approval(proposed_action, context)
    approval_provider = RecordingApprovalProvider(approval)
    clock = FixedApprovalClock(APPROVED_AT)
    runtime = GovernedActionRuntime(
        authorizer=_authorizer(),
        executor=executor,
        approval_provider=approval_provider,
        approval_clock=clock,
    )

    evidence = runtime.execute(proposed_action, context)

    assert executor.actions == [proposed_action]
    assert evidence.authorization.outcome == "require_human_approval"
    assert evidence.approval_status == "validated"
    assert evidence.human_approval == approval
    assert evidence.execution_occurred is True
    assert approval_provider.claim_calls == 1
    assert clock.calls == 1


def test_not_yet_valid_approval_is_consumed_and_blocked() -> None:
    """Block future-dated approval and require fresh evidence after the failed claim."""
    executor = RecordingActionExecutor()
    proposed_action = _remediation_action()
    context = _context()
    approval = _approval(proposed_action, context)
    approval_provider = RecordingApprovalProvider(approval)
    clock = FixedApprovalClock(APPROVED_AT - timedelta(seconds=1))
    runtime = GovernedActionRuntime(
        authorizer=_authorizer(),
        executor=executor,
        approval_provider=approval_provider,
        approval_clock=clock,
    )

    first = runtime.execute(proposed_action, context)
    second = runtime.execute(proposed_action, context)

    assert first.approval_status == "not_yet_valid"
    assert first.human_approval == approval
    assert first.execution_occurred is False
    assert second.approval_status == "missing"
    assert second.execution_occurred is False
    assert executor.actions == []
    assert approval_provider.claim_calls == 2
    assert clock.calls == 1


def test_expired_approval_is_consumed_at_exclusive_expiry_boundary() -> None:
    """Treat expires_at as exclusive and prevent stale approval from being retried."""
    executor = RecordingActionExecutor()
    proposed_action = _remediation_action()
    context = _context()
    approval = _approval(proposed_action, context)
    approval_provider = RecordingApprovalProvider(approval)
    clock = FixedApprovalClock(EXPIRES_AT)
    runtime = GovernedActionRuntime(
        authorizer=_authorizer(),
        executor=executor,
        approval_provider=approval_provider,
        approval_clock=clock,
    )

    first = runtime.execute(proposed_action, context)
    second = runtime.execute(proposed_action, context)

    assert first.authorization.outcome == "require_human_approval"
    assert first.approval_status == "expired"
    assert first.human_approval == approval
    assert first.execution_occurred is False
    assert second.approval_status == "missing"
    assert second.execution_occurred is False
    assert executor.actions == []
    assert approval_provider.claim_calls == 2
    assert clock.calls == 1


def test_consumed_valid_approval_cannot_execute_same_action_twice() -> None:
    """Require a fresh human approval for every repeated mutable execution."""
    executor = RecordingActionExecutor()
    proposed_action = _remediation_action()
    context = _context()
    approval_provider = RecordingApprovalProvider(_approval(proposed_action, context))
    clock = FixedApprovalClock(VALID_NOW)
    runtime = GovernedActionRuntime(
        authorizer=_authorizer(),
        executor=executor,
        approval_provider=approval_provider,
        approval_clock=clock,
    )

    first = runtime.execute(proposed_action, context)
    second = runtime.execute(proposed_action, context)

    assert first.approval_status == "validated"
    assert first.execution_occurred is True
    assert second.authorization.outcome == "require_human_approval"
    assert second.approval_status == "missing"
    assert second.execution_occurred is False
    assert executor.actions == [proposed_action]
    assert approval_provider.claim_calls == 2
    assert clock.calls == 1


def test_executor_failure_does_not_restore_claimed_approval() -> None:
    """Fail closed after a side-effect attempt instead of replaying the same approval."""
    executor = FailingActionExecutor()
    proposed_action = _remediation_action()
    context = _context()
    approval_provider = RecordingApprovalProvider(_approval(proposed_action, context))
    clock = FixedApprovalClock(VALID_NOW)
    runtime = GovernedActionRuntime(
        authorizer=_authorizer(),
        executor=executor,
        approval_provider=approval_provider,
        approval_clock=clock,
    )

    with pytest.raises(RuntimeError, match="executor failed"):
        runtime.execute(proposed_action, context)

    second = runtime.execute(proposed_action, context)

    assert second.authorization.outcome == "require_human_approval"
    assert second.approval_status == "missing"
    assert second.execution_occurred is False
    assert executor.calls == 1
    assert approval_provider.claim_calls == 2
    assert clock.calls == 1


def test_mismatched_approval_fails_before_clock_and_executor() -> None:
    """Reject mismatched scope after claim without treating time as authority."""
    executor = RecordingActionExecutor()
    proposed_action = _remediation_action()
    context = _context()
    mismatched_approval = _approval(
        _remediation_action(resource="finding:other"),
        context,
    )
    approval_provider = RecordingApprovalProvider(mismatched_approval)
    runtime = GovernedActionRuntime(
        authorizer=_authorizer(),
        executor=executor,
        approval_provider=approval_provider,
        approval_clock=UnexpectedApprovalClock(),
    )

    evidence = runtime.execute(proposed_action, context)

    assert executor.actions == []
    assert evidence.authorization.outcome == "require_human_approval"
    assert evidence.approval_status == "invalid"
    assert evidence.human_approval == mismatched_approval
    assert evidence.execution_occurred is False
    assert approval_provider.claim_calls == 1


def test_naive_runtime_clock_fails_closed_after_claim() -> None:
    """Reject an untrusted temporal boundary before mutable execution."""
    executor = RecordingActionExecutor()
    proposed_action = _remediation_action()
    context = _context()
    approval_provider = RecordingApprovalProvider(_approval(proposed_action, context))
    runtime = GovernedActionRuntime(
        authorizer=_authorizer(),
        executor=executor,
        approval_provider=approval_provider,
        approval_clock=FixedApprovalClock(datetime(2026, 9, 5, 20, 5)),
    )

    with pytest.raises(RuntimeError, match="timezone-aware"):
        runtime.execute(proposed_action, context)

    second = runtime.execute(proposed_action, context)

    assert second.approval_status == "missing"
    assert second.execution_occurred is False
    assert executor.actions == []
    assert approval_provider.claim_calls == 2


def test_unknown_action_fails_closed_before_executor() -> None:
    """Keep action escalation outside the executor through fail-closed authorization."""
    executor = RecordingActionExecutor()
    runtime = GovernedActionRuntime(authorizer=_authorizer(), executor=executor)

    evidence = runtime.execute(
        _vulnerability_action("delete_vulnerability"),
        _context(),
    )

    assert executor.actions == []
    assert evidence.authorization.outcome == "deny"
    assert evidence.authorization.reason == "no_matching_rule"
    assert evidence.execution_occurred is False


def test_resource_escalation_fails_closed_before_executor() -> None:
    """Keep an unauthorized target outside the executor for an allowed action name."""
    executor = RecordingActionExecutor()
    runtime = GovernedActionRuntime(authorizer=_authorizer(), executor=executor)

    evidence = runtime.execute(
        ProposedAction(
            action="read_vulnerability",
            resource="CVE-2026-DEMO-999",
            environment="test",
        ),
        _context(),
    )

    assert executor.actions == []
    assert evidence.authorization.outcome == "deny"
    assert evidence.authorization.reason == "no_matching_rule"
    assert evidence.execution_occurred is False


def test_authorization_failure_cannot_fall_through_to_executor() -> None:
    """Propagate authorization failure without executing the proposed action."""
    executor = RecordingActionExecutor()
    runtime = GovernedActionRuntime(authorizer=FailingAuthorizer(), executor=executor)

    with pytest.raises(RuntimeError, match="authorization unavailable"):
        runtime.execute(_vulnerability_action("read_vulnerability"), _context())

    assert executor.actions == []
