"""Tests for CrewAI consumption of the governed action runtime."""

from agentic_lab.adapters.crewai.action_flow import (
    CrewAIGovernedActionFlow,
    run_governed_action_flow,
)
from agentic_lab.adapters.fixtures.finding_actions import (
    ACKNOWLEDGE_FINDING_ACTION,
    InMemoryFindingAcknowledgementExecutor,
)
from agentic_lab.application.action_authorization import (
    ActionAuthorizationRuleKey,
    ActionContext,
    AuthorizationOutcome,
    ProposedAction,
    StaticActionAuthorizationPolicy,
)
from agentic_lab.application.action_runtime import GovernedActionRuntime

_FINDING_RESOURCE = "finding:demo-001"
_ALLOWED_CALLER = "remediation-agent"


def _runtime(
    executor: InMemoryFindingAcknowledgementExecutor,
) -> GovernedActionRuntime:
    rules: dict[ActionAuthorizationRuleKey, AuthorizationOutcome] = {
        (
            _ALLOWED_CALLER,
            "trusted_composition",
            ACKNOWLEDGE_FINDING_ACTION,
            _FINDING_RESOURCE,
            "test",
        ): "allow",
        (
            _ALLOWED_CALLER,
            "trusted_composition",
            ACKNOWLEDGE_FINDING_ACTION,
            _FINDING_RESOURCE,
            "staging",
        ): "deny",
        (
            _ALLOWED_CALLER,
            "trusted_composition",
            ACKNOWLEDGE_FINDING_ACTION,
            _FINDING_RESOURCE,
            "production",
        ): "require_human_approval",
    }
    return GovernedActionRuntime(
        authorizer=StaticActionAuthorizationPolicy(rules),
        executor=executor,
    )


def _action(
    *,
    resource: str = _FINDING_RESOURCE,
    environment: str = "test",
) -> ProposedAction:
    return ProposedAction(
        action=ACKNOWLEDGE_FINDING_ACTION,
        resource=resource,
        environment=environment,
    )


def _context(caller_id: str = _ALLOWED_CALLER) -> ActionContext:
    return ActionContext(caller_id=caller_id)


def test_crewai_governed_action_flow_suppresses_console_events() -> None:
    """Keep the minimal security experiment free from framework event noise."""
    executor = InMemoryFindingAcknowledgementExecutor([_FINDING_RESOURCE])
    flow = CrewAIGovernedActionFlow(
        runtime=_runtime(executor),
        context=_context(),
        proposed_action=_action(),
    )

    assert flow.suppress_flow_events is True


def test_crewai_allowed_action_executes_through_governed_runtime() -> None:
    """Allow CrewAI orchestration without moving authorization into the framework."""
    executor = InMemoryFindingAcknowledgementExecutor([_FINDING_RESOURCE])

    evidence = run_governed_action_flow(
        _runtime(executor),
        _context(),
        _action(),
    )

    assert evidence.authorization.outcome == "allow"
    assert evidence.execution_occurred is True
    assert executor.is_acknowledged(_FINDING_RESOURCE) is True
    assert executor.execution_count == 1


def test_crewai_explicit_deny_has_zero_side_effect() -> None:
    """Preserve application-owned deny enforcement through CrewAI Flow."""
    executor = InMemoryFindingAcknowledgementExecutor([_FINDING_RESOURCE])

    evidence = run_governed_action_flow(
        _runtime(executor),
        _context(),
        _action(environment="staging"),
    )

    assert evidence.authorization.outcome == "deny"
    assert evidence.authorization.reason == "explicit_deny"
    assert evidence.execution_occurred is False
    assert executor.is_acknowledged(_FINDING_RESOURCE) is False
    assert executor.execution_count == 0


def test_crewai_approval_required_has_zero_side_effect_without_approval() -> None:
    """Do not let CrewAI turn approval-required into framework-local approval."""
    executor = InMemoryFindingAcknowledgementExecutor([_FINDING_RESOURCE])

    evidence = run_governed_action_flow(
        _runtime(executor),
        _context(),
        _action(environment="production"),
    )

    assert evidence.authorization.outcome == "require_human_approval"
    assert evidence.approval_status == "missing"
    assert evidence.execution_occurred is False
    assert executor.is_acknowledged(_FINDING_RESOURCE) is False
    assert executor.execution_count == 0


def test_crewai_caller_mismatch_fails_closed_before_mutation() -> None:
    """Keep trusted caller identity outside framework-controlled action state."""
    executor = InMemoryFindingAcknowledgementExecutor([_FINDING_RESOURCE])

    evidence = run_governed_action_flow(
        _runtime(executor),
        _context("unprivileged-agent"),
        _action(),
    )

    assert evidence.authorization.outcome == "deny"
    assert evidence.authorization.reason == "no_matching_rule"
    assert evidence.execution_occurred is False
    assert executor.is_acknowledged(_FINDING_RESOURCE) is False
    assert executor.execution_count == 0


def test_crewai_resource_escalation_fails_closed_before_mutation() -> None:
    """Block resource substitution before the mutable adapter can run."""
    executor = InMemoryFindingAcknowledgementExecutor([_FINDING_RESOURCE])

    evidence = run_governed_action_flow(
        _runtime(executor),
        _context(),
        _action(resource="finding:demo-999"),
    )

    assert evidence.authorization.outcome == "deny"
    assert evidence.authorization.reason == "no_matching_rule"
    assert evidence.execution_occurred is False
    assert executor.is_acknowledged(_FINDING_RESOURCE) is False
    assert executor.execution_count == 0
