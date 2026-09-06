"""Component integration tests for governed mutable action execution."""

from datetime import UTC, datetime, timedelta

import pytest

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
    AuthorizationOutcome,
    ProposedAction,
    StaticActionAuthorizationPolicy,
)
from agentic_lab.application.action_runtime import (
    GovernedActionExecutionError,
    GovernedActionRuntime,
)

FINDING_RESOURCE = "finding:demo-001"
REMEDIATION_AGENT = "remediation-agent"
APPROVED_AT = datetime(2026, 9, 5, 20, 0, tzinfo=UTC)
VALID_NOW = APPROVED_AT + timedelta(minutes=5)
EXPIRES_AT = APPROVED_AT + timedelta(minutes=15)


class FixedApprovalClock:
    """Return deterministic trusted time for component integration."""

    def now(self) -> datetime:
        """Return one valid instant inside the approval window."""
        return VALID_NOW


def _runtime(
    executor: InMemoryFindingAcknowledgementExecutor,
) -> GovernedActionRuntime:
    rules: dict[ActionAuthorizationRuleKey, AuthorizationOutcome] = {
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
    return GovernedActionRuntime(
        authorizer=StaticActionAuthorizationPolicy(rules),
        executor=executor,
    )


def _context(caller_id: str = REMEDIATION_AGENT) -> ActionContext:
    return ActionContext(caller_id=caller_id)


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


def test_allowed_action_mutates_exact_authorized_resource() -> None:
    """Apply the real side effect only after an exact trusted-caller allow decision."""
    executor = InMemoryFindingAcknowledgementExecutor([FINDING_RESOURCE])
    context = _context()

    evidence = _runtime(executor).execute(_action(), context)

    assert evidence.context == context
    assert evidence.authorization.outcome == "allow"
    assert evidence.approval_status == "not_applicable"
    assert evidence.execution_occurred is True
    assert executor.is_acknowledged(FINDING_RESOURCE) is True
    assert executor.execution_count == 1


def test_different_caller_has_zero_side_effect_for_same_scope() -> None:
    """Keep identical action scope blocked when the trusted principal does not match."""
    executor = InMemoryFindingAcknowledgementExecutor([FINDING_RESOURCE])

    evidence = _runtime(executor).execute(
        _action(),
        _context("observer-agent"),
    )

    assert evidence.authorization.outcome == "deny"
    assert evidence.authorization.reason == "no_matching_rule"
    assert evidence.execution_occurred is False
    assert executor.is_acknowledged(FINDING_RESOURCE) is False
    assert executor.execution_count == 0


def test_denied_action_has_zero_side_effect() -> None:
    """Keep explicit-deny state outside the mutable adapter."""
    executor = InMemoryFindingAcknowledgementExecutor([FINDING_RESOURCE])

    evidence = _runtime(executor).execute(
        _action(environment="staging"),
        _context(),
    )

    assert evidence.authorization.outcome == "deny"
    assert evidence.execution_occurred is False
    assert executor.is_acknowledged(FINDING_RESOURCE) is False
    assert executor.execution_count == 0


def test_approval_required_action_has_zero_side_effect_without_approval() -> None:
    """Keep approval-required production state blocked when HITL evidence is absent."""
    executor = InMemoryFindingAcknowledgementExecutor([FINDING_RESOURCE])

    evidence = _runtime(executor).execute(
        _action(environment="production"),
        _context(),
    )

    assert evidence.authorization.outcome == "require_human_approval"
    assert evidence.approval_status == "missing"
    assert evidence.execution_occurred is False
    assert executor.is_acknowledged(FINDING_RESOURCE) is False
    assert executor.execution_count == 0


def test_exact_trusted_approval_allows_only_approved_mutation() -> None:
    """Apply the production mutation only after explicit trusted approval evidence."""
    executor = InMemoryFindingAcknowledgementExecutor([FINDING_RESOURCE])
    proposed_action = _action(environment="production")
    context = _context()
    approval = HumanApprovalEvidence(
        approval_id="approval-001",
        approver_id="soc-reviewer",
        proposed_action=proposed_action,
        context=context,
        approved_at=APPROVED_AT,
        expires_at=EXPIRES_AT,
    )
    rules: dict[ActionAuthorizationRuleKey, AuthorizationOutcome] = {
        (
            REMEDIATION_AGENT,
            "trusted_composition",
            "acknowledge_finding",
            FINDING_RESOURCE,
            "production",
        ): "require_human_approval",
    }
    runtime = GovernedActionRuntime(
        authorizer=StaticActionAuthorizationPolicy(rules),
        executor=executor,
        approval_provider=InMemoryActionApprovalProvider([approval]),
        approval_clock=FixedApprovalClock(),
        approver_authorizer=StaticActionApproverAuthorizationPolicy(
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
        ),
    )

    evidence = runtime.execute(proposed_action, context)

    assert evidence.authorization.outcome == "require_human_approval"
    assert evidence.approval_status == "validated"
    assert evidence.human_approval == approval
    assert evidence.execution_occurred is True
    assert executor.is_acknowledged(FINDING_RESOURCE) is True
    assert executor.execution_count == 1


def test_scope_escalation_has_zero_side_effect() -> None:
    """Block an untrusted resource substitution before it reaches the adapter."""
    executor = InMemoryFindingAcknowledgementExecutor([FINDING_RESOURCE])

    evidence = _runtime(executor).execute(
        _action(resource="finding:demo-999"),
        _context(),
    )

    assert evidence.authorization.outcome == "deny"
    assert evidence.authorization.reason == "no_matching_rule"
    assert evidence.execution_occurred is False
    assert executor.is_acknowledged(FINDING_RESOURCE) is False
    assert executor.execution_count == 0


def test_authorized_but_missing_resource_fails_without_mutation() -> None:
    """Keep authorization distinct from successful tool execution."""
    missing_resource = "finding:missing"
    rules: dict[ActionAuthorizationRuleKey, AuthorizationOutcome] = {
        (
            REMEDIATION_AGENT,
            "trusted_composition",
            "acknowledge_finding",
            missing_resource,
            "test",
        ): "allow",
    }
    executor = InMemoryFindingAcknowledgementExecutor([FINDING_RESOURCE])
    runtime = GovernedActionRuntime(
        authorizer=StaticActionAuthorizationPolicy(rules),
        executor=executor,
    )

    with pytest.raises(GovernedActionExecutionError) as exc_info:
        runtime.execute(_action(resource=missing_resource), _context())

    error = exc_info.value
    evidence = error.evidence

    assert isinstance(error.__cause__, LookupError)
    assert str(error.__cause__) == "finding does not exist"
    assert evidence.authorization.outcome == "allow"
    assert evidence.approval_status == "not_applicable"
    assert evidence.execution_attempted is True
    assert evidence.external_side_effect_state == "unknown"
    assert evidence.failure_reason == "executor_error"
    assert "finding does not exist" not in evidence.model_dump_json()
    assert executor.is_acknowledged(FINDING_RESOURCE) is False
    assert executor.execution_count == 0
