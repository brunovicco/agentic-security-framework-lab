"""Tests for structured evidence when an authorized governed executor raises."""

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from agentic_lab.application.action_approval import ApprovalClaim, HumanApprovalEvidence
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
from agentic_lab.application.action_runtime import (
    ActionExecutionFailureEvidence,
    GovernedActionExecutionError,
    GovernedActionRuntime,
)

CALLER_ID = "remediation-agent"
APPROVER_ID = "soc-reviewer"
RESOURCE = "finding:demo-001"
APPROVED_AT = datetime(2026, 9, 6, 0, 0, tzinfo=UTC)
EXPIRES_AT = APPROVED_AT + timedelta(minutes=15)
VALID_NOW = APPROVED_AT + timedelta(minutes=5)
SECRET_ERROR_TEXT = "executor-secret-detail-49"


class FailingExecutor:
    """Fail deterministically after the governed runtime crosses the executor boundary."""

    def __init__(self) -> None:
        self.calls = 0

    def execute(self, proposed_action: ProposedAction) -> None:
        """Record one executor invocation and raise a sensitive synthetic error."""
        self.calls += 1
        raise RuntimeError(f"{SECRET_ERROR_TEXT}:{proposed_action.action}")


class OneShotApprovalProvider:
    """Return one trusted approval claim and then fail closed as missing."""

    def __init__(self, approval: HumanApprovalEvidence | None) -> None:
        self._approval = approval
        self.calls = 0

    def claim_approval(
        self,
        proposed_action: ProposedAction,
        context: ActionContext,
    ) -> ApprovalClaim:
        """Consume one configured approval without rebinding its scope."""
        del proposed_action, context
        self.calls += 1
        approval = self._approval
        self._approval = None
        if approval is None:
            return ApprovalClaim(status="missing")
        return ApprovalClaim(status="claimed", approval=approval)


class FixedClock:
    """Return one deterministic timezone-aware current time."""

    def now(self) -> datetime:
        """Return a time inside the synthetic approval validity interval."""
        return VALID_NOW


def _context() -> ActionContext:
    return ActionContext(caller_id=CALLER_ID, identity_source="trusted_composition")


def _action(
    *,
    action: str = "acknowledge_finding",
    environment: str = "production",
) -> ProposedAction:
    return ProposedAction(action=action, resource=RESOURCE, environment=environment)


def _caller_authorizer() -> StaticActionAuthorizationPolicy:
    rules: dict[ActionAuthorizationRuleKey, AuthorizationOutcome] = {
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
        (
            CALLER_ID,
            "trusted_composition",
            "acknowledge_finding",
            RESOURCE,
            "production",
        ): "require_human_approval",
    }
    return StaticActionAuthorizationPolicy(rules)


def _approver_authorizer() -> StaticActionApproverAuthorizationPolicy:
    return StaticActionApproverAuthorizationPolicy(
        {
            (
                APPROVER_ID,
                CALLER_ID,
                "trusted_composition",
                "acknowledge_finding",
                RESOURCE,
                "production",
            ): "allow"
        }
    )


def _approval(
    proposed_action: ProposedAction,
    context: ActionContext,
) -> HumanApprovalEvidence:
    return HumanApprovalEvidence(
        approval_id="approval-phase49-001",
        approver_id=APPROVER_ID,
        proposed_action=proposed_action,
        context=context,
        approved_at=APPROVED_AT,
        expires_at=EXPIRES_AT,
    )


def _approver_allow() -> ApproverAuthorizationDecision:
    return ApproverAuthorizationDecision(outcome="allow", reason="explicit_allow")


def test_direct_allow_failure_evidence_is_structurally_valid() -> None:
    """Represent an attempted direct execution without inventing HITL evidence."""
    action = _action(action="read_finding", environment="test")
    context = _context()

    evidence = ActionExecutionFailureEvidence(
        proposed_action=action,
        context=context,
        authorization=_caller_authorizer().authorize(action, context),
        approval_status="not_applicable",
        human_approval=None,
    )

    assert evidence.execution_attempted is True
    assert evidence.external_side_effect_state == "unknown"
    assert evidence.failure_reason == "executor_error"
    assert evidence.approver_authorization is None


def test_hitl_failure_evidence_is_structurally_valid() -> None:
    """Preserve exact approval authority without claiming executor success."""
    action = _action()
    context = _context()
    approval = _approval(action, context)

    evidence = ActionExecutionFailureEvidence(
        proposed_action=action,
        context=context,
        authorization=_caller_authorizer().authorize(action, context),
        approval_status="validated",
        human_approval=approval,
        approver_authorization=_approver_allow(),
    )

    assert evidence.human_approval == approval
    assert evidence.execution_attempted is True
    assert evidence.external_side_effect_state == "unknown"


def test_failure_evidence_rejects_caller_deny() -> None:
    """Do not claim executor invocation for a caller path that must stop before execution."""
    action = _action(action="delete_finding")
    context = _context()

    with pytest.raises(ValidationError, match="requires executable caller authorization"):
        ActionExecutionFailureEvidence(
            proposed_action=action,
            context=context,
            authorization=_caller_authorizer().authorize(action, context),
            approval_status="not_applicable",
            human_approval=None,
        )


def test_direct_failure_evidence_rejects_hitl_payload() -> None:
    """Keep direct caller allow separate from human approval authority."""
    action = _action(action="read_finding", environment="test")
    context = _context()

    with pytest.raises(ValidationError, match="requires not_applicable approval status"):
        ActionExecutionFailureEvidence(
            proposed_action=action,
            context=context,
            authorization=_caller_authorizer().authorize(action, context),
            approval_status="validated",
            human_approval=_approval(action, context),
            approver_authorization=_approver_allow(),
        )


def test_hitl_failure_evidence_requires_validated_approval_state() -> None:
    """Do not cross the executor boundary from an incomplete HITL lifecycle state."""
    action = _action()
    context = _context()

    with pytest.raises(ValidationError, match="requires validated approval status"):
        ActionExecutionFailureEvidence(
            proposed_action=action,
            context=context,
            authorization=_caller_authorizer().authorize(action, context),
            approval_status="missing",
            human_approval=None,
        )


def test_hitl_failure_evidence_requires_exact_bound_approval() -> None:
    """Reject failure evidence that associates executor authority with another action scope."""
    action = _action()
    context = _context()
    mismatched = _approval(_action(action="other_action"), context)

    with pytest.raises(ValidationError, match="requires exact-bound human approval evidence"):
        ActionExecutionFailureEvidence(
            proposed_action=action,
            context=context,
            authorization=_caller_authorizer().authorize(action, context),
            approval_status="validated",
            human_approval=mismatched,
            approver_authorization=_approver_allow(),
        )


def test_hitl_failure_evidence_requires_approver_allow() -> None:
    """Do not represent an executor attempt after terminal approver denial."""
    action = _action()
    context = _context()

    with pytest.raises(ValidationError, match="requires an allow approver decision"):
        ActionExecutionFailureEvidence(
            proposed_action=action,
            context=context,
            authorization=_caller_authorizer().authorize(action, context),
            approval_status="validated",
            human_approval=_approval(action, context),
            approver_authorization=ApproverAuthorizationDecision(
                outcome="deny",
                reason="explicit_deny",
            ),
        )


def test_runtime_direct_executor_failure_carries_safe_structured_evidence() -> None:
    """Preserve caller authority and uncertainty without copying raw executor details."""
    executor = FailingExecutor()
    action = _action(action="read_finding", environment="test")
    context = _context()
    runtime = GovernedActionRuntime(authorizer=_caller_authorizer(), executor=executor)

    with pytest.raises(GovernedActionExecutionError) as exc_info:
        runtime.execute(action, context)

    error = exc_info.value
    evidence = error.evidence
    serialized = evidence.model_dump_json()

    assert str(error) == "governed action executor failed"
    assert isinstance(error.__cause__, RuntimeError)
    assert evidence.proposed_action == action
    assert evidence.context == context
    assert evidence.authorization.outcome == "allow"
    assert evidence.approval_status == "not_applicable"
    assert evidence.execution_attempted is True
    assert evidence.external_side_effect_state == "unknown"
    assert evidence.failure_reason == "executor_error"
    assert SECRET_ERROR_TEXT not in serialized
    assert SECRET_ERROR_TEXT not in str(error)
    assert executor.calls == 1


def test_runtime_hitl_executor_failure_keeps_approval_consumed() -> None:
    """Require fresh approval after a failed executor attempt and preserve failure authority."""
    executor = FailingExecutor()
    action = _action()
    context = _context()
    approval = _approval(action, context)
    provider = OneShotApprovalProvider(approval)
    runtime = GovernedActionRuntime(
        authorizer=_caller_authorizer(),
        executor=executor,
        approval_provider=provider,
        approval_clock=FixedClock(),
        approver_authorizer=_approver_authorizer(),
    )

    with pytest.raises(GovernedActionExecutionError) as exc_info:
        runtime.execute(action, context)

    evidence = exc_info.value.evidence
    retry = runtime.execute(action, context)

    assert evidence.authorization.outcome == "require_human_approval"
    assert evidence.approval_status == "validated"
    assert evidence.human_approval == approval
    assert evidence.approver_authorization == _approver_allow()
    assert evidence.execution_attempted is True
    assert evidence.external_side_effect_state == "unknown"
    assert SECRET_ERROR_TEXT not in evidence.model_dump_json()
    assert retry.approval_status == "missing"
    assert retry.execution_occurred is False
    assert provider.calls == 2
    assert executor.calls == 1


def test_caller_deny_never_synthesizes_executor_failure() -> None:
    """Return normal deny evidence because the failing executor boundary is never crossed."""
    executor = FailingExecutor()
    action = _action(action="delete_finding")
    runtime = GovernedActionRuntime(authorizer=_caller_authorizer(), executor=executor)

    evidence = runtime.execute(action, _context())

    assert evidence.authorization.outcome == "deny"
    assert evidence.execution_occurred is False
    assert executor.calls == 0


def test_missing_approval_never_synthesizes_executor_failure() -> None:
    """Return normal missing-approval evidence without invoking a failing executor."""
    executor = FailingExecutor()
    action = _action()
    runtime = GovernedActionRuntime(
        authorizer=_caller_authorizer(),
        executor=executor,
        approval_provider=OneShotApprovalProvider(None),
    )

    evidence = runtime.execute(action, _context())

    assert evidence.authorization.outcome == "require_human_approval"
    assert evidence.approval_status == "missing"
    assert evidence.execution_occurred is False
    assert executor.calls == 0
