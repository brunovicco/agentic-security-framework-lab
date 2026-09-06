"""Expose a host-authenticated governed mutable action through MCP v2 STDIO."""

import os

from mcp import MCPError
from mcp.server import MCPServer
from mcp.types import INTERNAL_ERROR, ToolAnnotations
from pydantic import BaseModel, ConfigDict, Field, SecretStr

from agentic_lab.adapters.fixtures.action_identity import StaticApiKeyCallerAuthenticator
from agentic_lab.adapters.fixtures.finding_actions import (
    ACKNOWLEDGE_FINDING_ACTION,
    InMemoryFindingAcknowledgementExecutor,
)
from agentic_lab.application.action_authorization import (
    ActionAuthorizationRuleKey,
    AuthorizationOutcome,
    ProposedAction,
    StaticActionAuthorizationPolicy,
)
from agentic_lab.application.action_identity import CallerCredential
from agentic_lab.application.action_runtime import GovernedActionRuntime
from agentic_lab.application.authenticated_action_runtime import (
    AuthenticatedActionExecutionEvidence,
    AuthenticatedGovernedActionExecutionError,
    AuthenticatedGovernedActionRuntime,
)

_SERVER_NAME = "agentic-security-authenticated-governed-actions"
_CALLER_ID = "local-api-key-client"
_FINDING_RESOURCE = "finding:demo-001"
_FAILURE_RESOURCE = "finding:missing"
_CREDENTIAL_ENV = "AGENTIC_SECURITY_CALLER_API_KEY"
_VERIFICATION_DIGEST_ENV = "AGENTIC_SECURITY_ALLOWED_API_KEY_SHA256"


class FindingAcknowledgementState(BaseModel):
    """Expose independent observable state for the synthetic finding fixture."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    resource: str
    acknowledged: bool
    execution_count: int = Field(ge=0)


mcp = MCPServer(_SERVER_NAME)

_executor = InMemoryFindingAcknowledgementExecutor([_FINDING_RESOURCE])
_runtime_and_credential: tuple[AuthenticatedGovernedActionRuntime, CallerCredential] | None = None


def _load_host_authenticated_runtime() -> tuple[
    AuthenticatedGovernedActionRuntime,
    CallerCredential,
]:
    """Capture host-only credential/configuration without exposing either as Tool input."""
    global _runtime_and_credential
    if _runtime_and_credential is not None:
        return _runtime_and_credential

    raw_credential = os.environ.pop(_CREDENTIAL_ENV, None)
    verification_digest = os.environ.pop(_VERIFICATION_DIGEST_ENV, None)
    if raw_credential is None or not raw_credential:
        raise RuntimeError(f"trusted MCP host must provide {_CREDENTIAL_ENV}")
    if verification_digest is None or not verification_digest:
        raise RuntimeError(f"trusted MCP host must provide {_VERIFICATION_DIGEST_ENV}")

    credential = CallerCredential(secret=SecretStr(raw_credential))
    authenticator = StaticApiKeyCallerAuthenticator.from_sha256_hex(
        {verification_digest: _CALLER_ID}
    )
    rules: dict[ActionAuthorizationRuleKey, AuthorizationOutcome] = {
        (
            _CALLER_ID,
            "api_key",
            ACKNOWLEDGE_FINDING_ACTION,
            _FINDING_RESOURCE,
            "test",
        ): "allow",
        (
            _CALLER_ID,
            "api_key",
            ACKNOWLEDGE_FINDING_ACTION,
            _FAILURE_RESOURCE,
            "test",
        ): "allow",
        (
            _CALLER_ID,
            "api_key",
            ACKNOWLEDGE_FINDING_ACTION,
            _FINDING_RESOURCE,
            "staging",
        ): "deny",
        (
            _CALLER_ID,
            "api_key",
            ACKNOWLEDGE_FINDING_ACTION,
            _FINDING_RESOURCE,
            "production",
        ): "require_human_approval",
    }
    action_runtime = GovernedActionRuntime(
        authorizer=StaticActionAuthorizationPolicy(rules),
        executor=_executor,
    )
    _runtime_and_credential = (
        AuthenticatedGovernedActionRuntime(
            authenticator=authenticator,
            action_runtime=action_runtime,
        ),
        credential,
    )
    return _runtime_and_credential


@mcp.tool(
    title="Acknowledge authenticated governed finding",
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=False,
        open_world_hint=False,
    ),
)
def acknowledge_finding(
    resource: str,
    environment: str,
) -> AuthenticatedActionExecutionEvidence:
    """Authenticate host credential before source-aware authorization and execution."""
    runtime, credential = _load_host_authenticated_runtime()
    proposed_action = ProposedAction(
        action=ACKNOWLEDGE_FINDING_ACTION,
        resource=resource,
        environment=environment,
    )
    try:
        return runtime.execute(proposed_action, credential)
    except AuthenticatedGovernedActionExecutionError as exc:
        raise MCPError(
            code=INTERNAL_ERROR,
            message="governed action execution outcome is unknown",
            data={
                "authenticated_execution_failure": exc.authenticated_evidence.model_dump(
                    mode="json"
                )
            },
        ) from exc


@mcp.tool(
    title="Get authenticated governed finding acknowledgement state",
    annotations=ToolAnnotations(
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
def get_finding_acknowledgement_state() -> FindingAcknowledgementState:
    """Return observable local state independently from authentication/action evidence."""
    return FindingAcknowledgementState(
        resource=_FINDING_RESOURCE,
        acknowledged=_executor.is_acknowledged(_FINDING_RESOURCE),
        execution_count=_executor.execution_count,
    )


if __name__ == "__main__":
    mcp.run(transport="stdio")
