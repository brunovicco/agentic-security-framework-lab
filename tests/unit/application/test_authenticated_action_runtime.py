"""Tests for authentication-first governed action composition."""

import pytest
from pydantic import SecretStr, ValidationError

from agentic_lab.adapters.fixtures.action_identity import StaticApiKeyCallerAuthenticator
from agentic_lab.application.action_authorization import (
    ActionContext,
    AuthorizationDecision,
    ProposedAction,
)
from agentic_lab.application.action_identity import (
    CallerAuthenticationDecision,
    CallerCredential,
)
from agentic_lab.application.action_runtime import ActionExecutionEvidence, GovernedActionRuntime
from agentic_lab.application.authenticated_action_runtime import (
    AuthenticatedActionExecutionEvidence,
    AuthenticatedGovernedActionRuntime,
)

API_KEY = "svc_test_7fe7d3d0f62c4d1e8c59f1968a6a1f45"
OTHER_API_KEY = "svc_test_3b8ce97ef10f4aad9a52235d3908b764"
CALLER_ID = "remediation-service"


class RecordingAuthorizer:
    """Record authorization calls and return one configured deterministic decision."""

    def __init__(self, decision: AuthorizationDecision) -> None:
        self._decision = decision
        self.calls: list[tuple[ProposedAction, ActionContext]] = []

    def authorize(
        self,
        proposed_action: ProposedAction,
        context: ActionContext,
    ) -> AuthorizationDecision:
        """Record the exact trusted context that reached authorization."""
        self.calls.append((proposed_action, context))
        return self._decision


class RecordingExecutor:
    """Record mutable executions that cross all application security boundaries."""

    def __init__(self) -> None:
        self.actions: list[ProposedAction] = []

    def execute(self, proposed_action: ProposedAction) -> None:
        """Record one already-authorized action."""
        self.actions.append(proposed_action)


def _credential(value: str) -> CallerCredential:
    return CallerCredential(secret=SecretStr(value))


def _action() -> ProposedAction:
    return ProposedAction(
        action="acknowledge_finding",
        resource="finding:demo-001",
        environment="test",
    )


def _runtime(
    decision: AuthorizationDecision,
) -> tuple[AuthenticatedGovernedActionRuntime, RecordingAuthorizer, RecordingExecutor]:
    authorizer = RecordingAuthorizer(decision)
    executor = RecordingExecutor()
    governed_runtime = GovernedActionRuntime(authorizer=authorizer, executor=executor)
    runtime = AuthenticatedGovernedActionRuntime(
        authenticator=StaticApiKeyCallerAuthenticator({API_KEY: CALLER_ID}),
        action_runtime=governed_runtime,
    )
    return runtime, authorizer, executor


def test_rejected_authentication_never_reaches_authorization_or_executor() -> None:
    """Fail closed before policy or mutable execution when credential verification fails."""
    runtime, authorizer, executor = _runtime(
        AuthorizationDecision(outcome="allow", reason="explicit_allow")
    )

    evidence = runtime.execute(_action(), _credential(OTHER_API_KEY))

    assert evidence.authentication.outcome == "rejected"
    assert evidence.authentication.context is None
    assert evidence.execution is None
    assert authorizer.calls == []
    assert executor.actions == []


def test_authenticated_caller_reaches_governed_runtime_with_derived_context() -> None:
    """Pass only the authenticated caller context into authorization and execution."""
    runtime, authorizer, executor = _runtime(
        AuthorizationDecision(outcome="allow", reason="explicit_allow")
    )
    proposed_action = _action()

    evidence = runtime.execute(proposed_action, _credential(API_KEY))

    assert evidence.authentication.outcome == "authenticated"
    assert evidence.authentication.context is not None
    context = evidence.authentication.context
    assert context.caller_id == CALLER_ID
    assert context.identity_source == "api_key"
    assert authorizer.calls == [(proposed_action, context)]
    assert executor.actions == [proposed_action]
    assert evidence.execution is not None
    assert evidence.execution.context == context
    assert evidence.execution.authorization.outcome == "allow"
    assert evidence.execution.execution_occurred is True


def test_authentication_success_does_not_override_authorization_deny() -> None:
    """Keep successful credential verification distinct from permission to act."""
    runtime, authorizer, executor = _runtime(
        AuthorizationDecision(outcome="deny", reason="explicit_deny")
    )
    proposed_action = _action()

    evidence = runtime.execute(proposed_action, _credential(API_KEY))

    assert evidence.authentication.outcome == "authenticated"
    assert evidence.authentication.context is not None
    assert authorizer.calls == [(proposed_action, evidence.authentication.context)]
    assert executor.actions == []
    assert evidence.execution is not None
    assert evidence.execution.authorization.outcome == "deny"
    assert evidence.execution.execution_occurred is False


def test_raw_credential_never_enters_returned_evidence() -> None:
    """Keep credential material outside authentication and execution evidence."""
    runtime, _, _ = _runtime(AuthorizationDecision(outcome="allow", reason="explicit_allow"))

    evidence = runtime.execute(_action(), _credential(API_KEY))

    assert API_KEY not in evidence.model_dump_json()
    assert API_KEY not in repr(evidence)


def test_rejected_authentication_cannot_be_paired_with_execution_evidence() -> None:
    """Reject evidence that claims execution after failed caller authentication."""
    context = ActionContext(caller_id=CALLER_ID, identity_source="api_key")
    execution = ActionExecutionEvidence(
        proposed_action=_action(),
        context=context,
        authorization=AuthorizationDecision(outcome="allow", reason="explicit_allow"),
        approval_status="not_applicable",
        human_approval=None,
        execution_occurred=True,
    )
    rejected = CallerAuthenticationDecision(
        outcome="rejected",
        reason="credential_rejected",
    )

    with pytest.raises(ValidationError, match="rejected authentication"):
        AuthenticatedActionExecutionEvidence(authentication=rejected, execution=execution)


def test_authenticated_evidence_requires_execution_for_exact_authenticated_context() -> None:
    """Reject missing or context-substituted execution evidence after authentication."""
    authenticated_context = ActionContext(caller_id=CALLER_ID, identity_source="api_key")
    authenticated = CallerAuthenticationDecision(
        outcome="authenticated",
        reason="credential_verified",
        context=authenticated_context,
    )

    with pytest.raises(ValidationError, match="requires execution evidence"):
        AuthenticatedActionExecutionEvidence(authentication=authenticated)

    mismatched_execution = ActionExecutionEvidence(
        proposed_action=_action(),
        context=ActionContext(caller_id="other-service", identity_source="api_key"),
        authorization=AuthorizationDecision(outcome="deny", reason="explicit_deny"),
        approval_status="not_applicable",
        human_approval=None,
        execution_occurred=False,
    )
    with pytest.raises(ValidationError, match="must match authenticated caller context"):
        AuthenticatedActionExecutionEvidence(
            authentication=authenticated,
            execution=mismatched_execution,
        )
