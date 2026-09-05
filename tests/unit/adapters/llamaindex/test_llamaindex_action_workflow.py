"""Tests for LlamaIndex Workflow consumption of the governed action runtime."""

from agentic_lab.adapters.fixtures.finding_actions import (
    ACKNOWLEDGE_FINDING_ACTION,
    InMemoryFindingAcknowledgementExecutor,
)
from agentic_lab.adapters.llamaindex.action_workflow import (
    LlamaIndexGovernedActionRuntime,
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


def _runtime(
    executor: InMemoryFindingAcknowledgementExecutor,
) -> GovernedActionRuntime:
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
    return GovernedActionRuntime(
        authorizer=StaticActionAuthorizationPolicy(rules),
        executor=executor,
    )


def _workflow_runtime(
    executor: InMemoryFindingAcknowledgementExecutor,
    caller_id: str = _ALLOWED_CALLER,
) -> LlamaIndexGovernedActionRuntime:
    return LlamaIndexGovernedActionRuntime(
        runtime=_runtime(executor),
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


def test_llamaindex_allowed_action_executes_through_governed_runtime() -> None:
    """Allow Workflow orchestration without moving authorization into LlamaIndex."""
    executor = InMemoryFindingAcknowledgementExecutor([_FINDING_RESOURCE])

    evidence = _workflow_runtime(executor).run(_action())

    assert evidence.authorization.outcome == "allow"
    assert evidence.execution_occurred is True
    assert executor.is_acknowledged(_FINDING_RESOURCE) is True
    assert executor.execution_count == 1


def test_llamaindex_explicit_deny_has_zero_side_effect() -> None:
    """Preserve application-owned deny enforcement through LlamaIndex Workflow."""
    executor = InMemoryFindingAcknowledgementExecutor([_FINDING_RESOURCE])

    evidence = _workflow_runtime(executor).run(_action(environment="staging"))

    assert evidence.authorization.outcome == "deny"
    assert evidence.authorization.reason == "explicit_deny"
    assert evidence.execution_occurred is False
    assert executor.is_acknowledged(_FINDING_RESOURCE) is False
    assert executor.execution_count == 0


def test_llamaindex_approval_required_has_zero_side_effect_without_approval() -> None:
    """Keep human approval outside LlamaIndex event orchestration."""
    executor = InMemoryFindingAcknowledgementExecutor([_FINDING_RESOURCE])

    evidence = _workflow_runtime(executor).run(_action(environment="production"))

    assert evidence.authorization.outcome == "require_human_approval"
    assert evidence.approval_status == "missing"
    assert evidence.execution_occurred is False
    assert executor.is_acknowledged(_FINDING_RESOURCE) is False
    assert executor.execution_count == 0


def test_llamaindex_caller_mismatch_fails_closed_before_mutation() -> None:
    """Bind authorization to constructor-injected caller context, not event data."""
    executor = InMemoryFindingAcknowledgementExecutor([_FINDING_RESOURCE])

    evidence = _workflow_runtime(executor, caller_id="unprivileged-agent").run(_action())

    assert evidence.authorization.outcome == "deny"
    assert evidence.authorization.reason == "no_matching_rule"
    assert evidence.execution_occurred is False
    assert executor.is_acknowledged(_FINDING_RESOURCE) is False
    assert executor.execution_count == 0


def test_llamaindex_resource_escalation_fails_closed_before_mutation() -> None:
    """Block a substituted resource before the mutable adapter can execute."""
    executor = InMemoryFindingAcknowledgementExecutor([_FINDING_RESOURCE])

    evidence = _workflow_runtime(executor).run(_action(resource="finding:demo-999"))

    assert evidence.authorization.outcome == "deny"
    assert evidence.authorization.reason == "no_matching_rule"
    assert evidence.execution_occurred is False
    assert executor.is_acknowledged(_FINDING_RESOURCE) is False
    assert executor.execution_count == 0
