"""Tests for authenticated evidence when governed execution crosses into failure."""

import pytest
from pydantic import SecretStr, ValidationError

from agentic_lab.adapters.fixtures.action_identity import StaticApiKeyCallerAuthenticator
from agentic_lab.application.action_authorization import (
    ActionAuthorizationRuleKey,
    ActionContext,
    AuthorizationDecision,
    AuthorizationOutcome,
    ProposedAction,
    StaticActionAuthorizationPolicy,
)
from agentic_lab.application.action_identity import (
    CallerAuthenticationDecision,
    CallerCredential,
)
from agentic_lab.application.action_runtime import (
    ActionExecutionFailureEvidence,
    GovernedActionExecutionError,
    GovernedActionRuntime,
)
from agentic_lab.application.authenticated_action_runtime import (
    AuthenticatedActionExecutionFailureEvidence,
    AuthenticatedGovernedActionExecutionError,
    AuthenticatedGovernedActionRuntime,
)

API_KEY = "svc_test_54b0a75105564fb4be0ac7ad660b6f96"
OTHER_API_KEY = "svc_test_a47b43dbef114d7897e90bbde3cd628b"
CALLER_ID = "remediation-service"
EXECUTOR_ERROR_TEXT = "synthetic executor failure detail"


class FailingExecutor:
    """Record invocations before raising one synthetic adapter failure."""

    def __init__(self) -> None:
        self.actions: list[ProposedAction] = []

    def execute(self, proposed_action: ProposedAction) -> None:
        """Record the attempt and fail after the executor boundary is crossed."""
        self.actions.append(proposed_action)
        raise LookupError(EXECUTOR_ERROR_TEXT)


def _action() -> ProposedAction:
    return ProposedAction(
        action="acknowledge_finding",
        resource="finding:demo-001",
        environment="test",
    )


def _credential(value: str) -> CallerCredential:
    return CallerCredential(secret=SecretStr(value))


def _runtime(executor: FailingExecutor) -> AuthenticatedGovernedActionRuntime:
    rules: dict[ActionAuthorizationRuleKey, AuthorizationOutcome] = {
        (
            CALLER_ID,
            "api_key",
            "acknowledge_finding",
            "finding:demo-001",
            "test",
        ): "allow",
    }
    return AuthenticatedGovernedActionRuntime(
        authenticator=StaticApiKeyCallerAuthenticator({API_KEY: CALLER_ID}),
        action_runtime=GovernedActionRuntime(
            authorizer=StaticActionAuthorizationPolicy(rules),
            executor=executor,
        ),
    )


def _action_failure(context: ActionContext) -> ActionExecutionFailureEvidence:
    return ActionExecutionFailureEvidence(
        proposed_action=_action(),
        context=context,
        authorization=AuthorizationDecision(outcome="allow", reason="explicit_allow"),
        approval_status="not_applicable",
        human_approval=None,
        approver_authorization=None,
    )


def test_authenticated_executor_failure_preserves_authentication_evidence() -> None:
    """Keep credential verification independently visible when the executor raises."""
    executor = FailingExecutor()
    runtime = _runtime(executor)
    proposed_action = _action()

    with pytest.raises(AuthenticatedGovernedActionExecutionError) as exc_info:
        runtime.execute(proposed_action, _credential(API_KEY))

    error = exc_info.value
    authenticated_evidence = error.authenticated_evidence
    action_failure = error.evidence

    assert isinstance(error, GovernedActionExecutionError)
    assert authenticated_evidence.authentication.outcome == "authenticated"
    assert authenticated_evidence.authentication.reason == "credential_verified"
    assert authenticated_evidence.authentication.context == action_failure.context
    assert authenticated_evidence.execution_failure == action_failure
    assert action_failure.authorization.outcome == "allow"
    assert action_failure.execution_attempted is True
    assert action_failure.external_side_effect_state == "unknown"
    assert executor.actions == [proposed_action]

    assert isinstance(error.__cause__, GovernedActionExecutionError)
    assert isinstance(error.__cause__.__cause__, LookupError)
    assert str(error.__cause__.__cause__) == EXECUTOR_ERROR_TEXT
    assert EXECUTOR_ERROR_TEXT not in authenticated_evidence.model_dump_json()
    assert EXECUTOR_ERROR_TEXT not in str(error)
    assert API_KEY not in authenticated_evidence.model_dump_json()
    assert API_KEY not in repr(authenticated_evidence)


def test_rejected_authentication_never_reaches_failing_executor() -> None:
    """Keep rejected credentials outside authorization and executor-failure evidence."""
    executor = FailingExecutor()
    runtime = _runtime(executor)

    evidence = runtime.execute(_action(), _credential(OTHER_API_KEY))

    assert evidence.authentication.outcome == "rejected"
    assert evidence.authentication.context is None
    assert evidence.execution is None
    assert executor.actions == []


def test_authenticated_failure_evidence_rejects_rejected_authentication() -> None:
    """Prevent a failed credential check from being attached to executor-failure evidence."""
    context = ActionContext(caller_id=CALLER_ID, identity_source="api_key")
    rejected = CallerAuthenticationDecision(
        outcome="rejected",
        reason="credential_rejected",
    )

    with pytest.raises(ValidationError, match="requires authenticated caller"):
        AuthenticatedActionExecutionFailureEvidence(
            authentication=rejected,
            execution_failure=_action_failure(context),
        )


def test_authenticated_failure_evidence_rejects_context_substitution() -> None:
    """Bind failure evidence to the exact context derived from credential verification."""
    authenticated_context = ActionContext(caller_id=CALLER_ID, identity_source="api_key")
    authenticated = CallerAuthenticationDecision(
        outcome="authenticated",
        reason="credential_verified",
        context=authenticated_context,
    )
    substituted_context = ActionContext(caller_id="other-service", identity_source="api_key")

    with pytest.raises(ValidationError, match="must match authenticated caller context"):
        AuthenticatedActionExecutionFailureEvidence(
            authentication=authenticated,
            execution_failure=_action_failure(substituted_context),
        )
