"""Tests for LangGraph consumption of the governed action runtime."""

from agentic_lab.adapters.fixtures.finding_actions import (
    InMemoryFindingAcknowledgementExecutor,
)
from agentic_lab.adapters.langgraph.action_graph import run_governed_action_graph
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


def test_langgraph_allowed_action_executes_through_governed_runtime() -> None:
    """Keep LangGraph orchestration outside the authorization authority boundary."""
    executor = InMemoryFindingAcknowledgementExecutor([FINDING_RESOURCE])

    output = run_governed_action_graph(_runtime(executor), _action())

    evidence = output["execution_evidence"]
    assert evidence.authorization.outcome == "allow"
    assert evidence.execution_occurred is True
    assert executor.is_acknowledged(FINDING_RESOURCE) is True
    assert executor.execution_count == 1


def test_langgraph_denied_action_has_zero_side_effect() -> None:
    """Preserve application-owned deny enforcement through the framework adapter."""
    executor = InMemoryFindingAcknowledgementExecutor([FINDING_RESOURCE])

    output = run_governed_action_graph(
        _runtime(executor),
        _action(environment="staging"),
    )

    evidence = output["execution_evidence"]
    assert evidence.authorization.outcome == "deny"
    assert evidence.execution_occurred is False
    assert executor.is_acknowledged(FINDING_RESOURCE) is False
    assert executor.execution_count == 0


def test_langgraph_approval_required_action_has_zero_side_effect() -> None:
    """Do not let framework orchestration turn approval-required into allow."""
    executor = InMemoryFindingAcknowledgementExecutor([FINDING_RESOURCE])

    output = run_governed_action_graph(
        _runtime(executor),
        _action(environment="production"),
    )

    evidence = output["execution_evidence"]
    assert evidence.authorization.outcome == "require_human_approval"
    assert evidence.execution_occurred is False
    assert executor.is_acknowledged(FINDING_RESOURCE) is False
    assert executor.execution_count == 0


def test_langgraph_resource_escalation_fails_closed_before_mutation() -> None:
    """Keep a substituted resource outside the executor through the same boundary."""
    executor = InMemoryFindingAcknowledgementExecutor([FINDING_RESOURCE])

    output = run_governed_action_graph(
        _runtime(executor),
        _action(resource="finding:demo-999"),
    )

    evidence = output["execution_evidence"]
    assert evidence.authorization.outcome == "deny"
    assert evidence.authorization.reason == "no_matching_rule"
    assert evidence.execution_occurred is False
    assert executor.is_acknowledged(FINDING_RESOURCE) is False
    assert executor.execution_count == 0


def test_langgraph_environment_escalation_fails_closed_before_mutation() -> None:
    """Keep an unknown environment outside the exact least-privilege scope."""
    executor = InMemoryFindingAcknowledgementExecutor([FINDING_RESOURCE])

    output = run_governed_action_graph(
        _runtime(executor),
        _action(environment="production-shadow"),
    )

    evidence = output["execution_evidence"]
    assert evidence.authorization.outcome == "deny"
    assert evidence.authorization.reason == "no_matching_rule"
    assert evidence.execution_occurred is False
    assert executor.is_acknowledged(FINDING_RESOURCE) is False
    assert executor.execution_count == 0


def test_langgraph_action_substitution_fails_closed_before_mutation() -> None:
    """Authorize the actual proposed operation rather than a broader tool capability."""
    executor = InMemoryFindingAcknowledgementExecutor([FINDING_RESOURCE])

    output = run_governed_action_graph(
        _runtime(executor),
        _action(action="delete_finding"),
    )

    evidence = output["execution_evidence"]
    assert evidence.authorization.outcome == "deny"
    assert evidence.authorization.reason == "no_matching_rule"
    assert evidence.execution_occurred is False
    assert executor.is_acknowledged(FINDING_RESOURCE) is False
    assert executor.execution_count == 0
