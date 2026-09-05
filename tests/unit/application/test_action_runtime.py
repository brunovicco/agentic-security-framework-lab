"""Tests for framework-neutral governed action runtime enforcement."""

import pytest

from agentic_lab.application.action_authorization import (
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


class RecordingActionExecutor:
    """Record actions that cross the runtime enforcement boundary."""

    def __init__(self) -> None:
        self.actions: list[ProposedAction] = []

    def execute(self, proposed_action: ProposedAction) -> None:
        """Record one executed action without performing an external side effect."""
        self.actions.append(proposed_action)


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
    rules: dict[tuple[str, str, str, str], AuthorizationOutcome] = {
        (REMEDIATION_AGENT, "read_vulnerability", VULNERABILITY_RESOURCE, "test"): "allow",
        (REMEDIATION_AGENT, "modify_vulnerability", VULNERABILITY_RESOURCE, "test"): "deny",
        (
            REMEDIATION_AGENT,
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


def test_allowed_action_reaches_executor_once() -> None:
    """Execute exactly once after an explicit allow for trusted caller and scope."""
    executor = RecordingActionExecutor()
    runtime = GovernedActionRuntime(authorizer=_authorizer(), executor=executor)
    proposed_action = _vulnerability_action("read_vulnerability")
    context = _context()

    evidence = runtime.execute(proposed_action, context)

    assert executor.actions == [proposed_action]
    assert evidence.proposed_action == proposed_action
    assert evidence.context == context
    assert evidence.authorization.outcome == "allow"
    assert evidence.execution_occurred is True


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
    assert evidence.execution_occurred is False


def test_denied_action_never_reaches_executor() -> None:
    """Block execution after an explicit deny decision."""
    executor = RecordingActionExecutor()
    runtime = GovernedActionRuntime(authorizer=_authorizer(), executor=executor)

    evidence = runtime.execute(
        _vulnerability_action("modify_vulnerability"),
        _context(),
    )

    assert executor.actions == []
    assert evidence.authorization.outcome == "deny"
    assert evidence.authorization.reason == "explicit_deny"
    assert evidence.execution_occurred is False


def test_approval_required_action_never_reaches_executor() -> None:
    """Block execution while human approval is still required."""
    executor = RecordingActionExecutor()
    runtime = GovernedActionRuntime(authorizer=_authorizer(), executor=executor)

    evidence = runtime.execute(
        ProposedAction(
            action="create_remediation_task",
            resource=REMEDIATION_RESOURCE,
            environment="production",
        ),
        _context(),
    )

    assert executor.actions == []
    assert evidence.authorization.outcome == "require_human_approval"
    assert evidence.execution_occurred is False


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
