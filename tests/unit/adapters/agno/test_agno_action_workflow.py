"""Tests for Agno Workflow consumption of the governed action runtime."""

import pytest

from agentic_lab.adapters.agno.action_workflow import AgnoGovernedActionRuntime
from agentic_lab.adapters.fixtures.finding_actions import (
    ACKNOWLEDGE_FINDING_ACTION,
    InMemoryFindingAcknowledgementExecutor,
)
from agentic_lab.application.action_authorization import (
    ActionContext,
    AuthorizationOutcome,
    ProposedAction,
    StaticActionAuthorizationPolicy,
)
from agentic_lab.application.action_runtime import GovernedActionRuntime

_FINDING_RESOURCE = "finding:demo-001"
_ALLOWED_CALLER = "remediation-agent"


class _FailingExecutor:
    """Record invocation count before raising a synthetic execution failure."""

    def __init__(self) -> None:
        self.calls = 0

    def execute(self, proposed_action: ProposedAction) -> None:
        self.calls += 1
        raise RuntimeError(f"synthetic failure for {proposed_action.resource}")


def _policy() -> StaticActionAuthorizationPolicy:
    rules: dict[tuple[str, str, str, str], AuthorizationOutcome] = {
        (
            _ALLOWED_CALLER,
            ACKNOWLEDGE_FINDING_ACTION,
            _FINDING_RESOURCE,
            "test",
        ): "allow",
        (
            _ALLOWED_CALLER,
            ACKNOWLEDGE_FINDING_ACTION,
            _FINDING_RESOURCE,
            "staging",
        ): "deny",
        (
            _ALLOWED_CALLER,
            ACKNOWLEDGE_FINDING_ACTION,
            _FINDING_RESOURCE,
            "production",
        ): "require_human_approval",
    }
    return StaticActionAuthorizationPolicy(rules)


def _workflow_runtime(
    executor: InMemoryFindingAcknowledgementExecutor,
    caller_id: str = _ALLOWED_CALLER,
) -> AgnoGovernedActionRuntime:
    return AgnoGovernedActionRuntime(
        runtime=GovernedActionRuntime(
            authorizer=_policy(),
            executor=executor,
        ),
        context=ActionContext(caller_id=caller_id),
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


def test_agno_allowed_action_executes_through_governed_runtime() -> None:
    """Allow Agno orchestration without moving authorization into the framework."""
    executor = InMemoryFindingAcknowledgementExecutor([_FINDING_RESOURCE])

    evidence = _workflow_runtime(executor).run(_action())

    assert evidence.authorization.outcome == "allow"
    assert evidence.execution_occurred is True
    assert executor.is_acknowledged(_FINDING_RESOURCE) is True
    assert executor.execution_count == 1


def test_agno_explicit_deny_has_zero_side_effect() -> None:
    """Preserve application-owned deny enforcement through Agno Workflow."""
    executor = InMemoryFindingAcknowledgementExecutor([_FINDING_RESOURCE])

    evidence = _workflow_runtime(executor).run(_action(environment="staging"))

    assert evidence.authorization.outcome == "deny"
    assert evidence.authorization.reason == "explicit_deny"
    assert evidence.execution_occurred is False
    assert executor.is_acknowledged(_FINDING_RESOURCE) is False
    assert executor.execution_count == 0


def test_agno_approval_required_has_zero_side_effect_without_approval() -> None:
    """Keep human approval outside Agno Workflow orchestration."""
    executor = InMemoryFindingAcknowledgementExecutor([_FINDING_RESOURCE])

    evidence = _workflow_runtime(executor).run(_action(environment="production"))

    assert evidence.authorization.outcome == "require_human_approval"
    assert evidence.approval_status == "missing"
    assert evidence.execution_occurred is False
    assert executor.is_acknowledged(_FINDING_RESOURCE) is False
    assert executor.execution_count == 0


def test_agno_caller_mismatch_fails_closed_before_mutation() -> None:
    """Bind authorization to constructor-injected caller context, not workflow input."""
    executor = InMemoryFindingAcknowledgementExecutor([_FINDING_RESOURCE])

    evidence = _workflow_runtime(executor, caller_id="unprivileged-agent").run(_action())

    assert evidence.authorization.outcome == "deny"
    assert evidence.authorization.reason == "no_matching_rule"
    assert evidence.execution_occurred is False
    assert executor.is_acknowledged(_FINDING_RESOURCE) is False
    assert executor.execution_count == 0


def test_agno_resource_escalation_fails_closed_before_mutation() -> None:
    """Block a substituted resource before the mutable adapter can execute."""
    executor = InMemoryFindingAcknowledgementExecutor([_FINDING_RESOURCE])

    evidence = _workflow_runtime(executor).run(_action(resource="finding:demo-999"))

    assert evidence.authorization.outcome == "deny"
    assert evidence.authorization.reason == "no_matching_rule"
    assert evidence.execution_occurred is False
    assert executor.is_acknowledged(_FINDING_RESOURCE) is False
    assert executor.execution_count == 0


def test_agno_mutable_step_does_not_retry_executor_failure() -> None:
    """Prevent framework retry policy from repeating a failed mutable execution."""
    executor = _FailingExecutor()
    runtime = AgnoGovernedActionRuntime(
        runtime=GovernedActionRuntime(
            authorizer=_policy(),
            executor=executor,
        ),
        context=ActionContext(caller_id=_ALLOWED_CALLER),
    )

    with pytest.raises(RuntimeError):
        runtime.run(_action())

    assert executor.calls == 1
