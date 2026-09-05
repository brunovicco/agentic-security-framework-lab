"""Component integration tests for governed mutable action execution."""

import pytest

from agentic_lab.adapters.fixtures.finding_actions import (
    InMemoryFindingAcknowledgementExecutor,
)
from agentic_lab.application.action_authorization import (
    AuthorizationOutcome,
    ProposedAction,
    StaticActionAuthorizationPolicy,
)
from agentic_lab.application.action_runtime import GovernedActionRuntime

FINDING_RESOURCE = "finding:demo-001"


def _runtime(
    executor: InMemoryFindingAcknowledgementExecutor,
) -> GovernedActionRuntime:
    rules: dict[tuple[str, str, str], AuthorizationOutcome] = {
        ("acknowledge_finding", FINDING_RESOURCE, "test"): "allow",
        ("acknowledge_finding", FINDING_RESOURCE, "staging"): "deny",
        (
            "acknowledge_finding",
            FINDING_RESOURCE,
            "production",
        ): "require_human_approval",
    }
    return GovernedActionRuntime(
        authorizer=StaticActionAuthorizationPolicy(rules),
        executor=executor,
    )


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
    """Apply the real in-memory side effect only after an exact allow decision."""
    executor = InMemoryFindingAcknowledgementExecutor([FINDING_RESOURCE])

    evidence = _runtime(executor).execute(_action())

    assert evidence.authorization.outcome == "allow"
    assert evidence.execution_occurred is True
    assert executor.is_acknowledged(FINDING_RESOURCE) is True
    assert executor.execution_count == 1


def test_denied_action_has_zero_side_effect() -> None:
    """Keep explicit-deny state outside the mutable adapter."""
    executor = InMemoryFindingAcknowledgementExecutor([FINDING_RESOURCE])

    evidence = _runtime(executor).execute(_action(environment="staging"))

    assert evidence.authorization.outcome == "deny"
    assert evidence.execution_occurred is False
    assert executor.is_acknowledged(FINDING_RESOURCE) is False
    assert executor.execution_count == 0


def test_approval_required_action_has_zero_side_effect() -> None:
    """Do not simulate human approval or mutate production state automatically."""
    executor = InMemoryFindingAcknowledgementExecutor([FINDING_RESOURCE])

    evidence = _runtime(executor).execute(_action(environment="production"))

    assert evidence.authorization.outcome == "require_human_approval"
    assert evidence.execution_occurred is False
    assert executor.is_acknowledged(FINDING_RESOURCE) is False
    assert executor.execution_count == 0


def test_scope_escalation_has_zero_side_effect() -> None:
    """Block an untrusted resource substitution before it reaches the adapter."""
    executor = InMemoryFindingAcknowledgementExecutor([FINDING_RESOURCE])

    evidence = _runtime(executor).execute(_action(resource="finding:demo-999"))

    assert evidence.authorization.outcome == "deny"
    assert evidence.authorization.reason == "no_matching_rule"
    assert evidence.execution_occurred is False
    assert executor.is_acknowledged(FINDING_RESOURCE) is False
    assert executor.execution_count == 0


def test_authorized_but_missing_resource_fails_without_mutation() -> None:
    """Keep authorization distinct from successful tool execution."""
    missing_resource = "finding:missing"
    rules: dict[tuple[str, str, str], AuthorizationOutcome] = {
        ("acknowledge_finding", missing_resource, "test"): "allow",
    }
    executor = InMemoryFindingAcknowledgementExecutor([FINDING_RESOURCE])
    runtime = GovernedActionRuntime(
        authorizer=StaticActionAuthorizationPolicy(rules),
        executor=executor,
    )

    with pytest.raises(LookupError, match="finding does not exist"):
        runtime.execute(_action(resource=missing_resource))

    assert executor.is_acknowledged(FINDING_RESOURCE) is False
    assert executor.execution_count == 0
