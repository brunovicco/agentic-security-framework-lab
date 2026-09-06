"""Expose a governed mutable action through an isolated MCP v2 server."""

from mcp import MCPError
from mcp.server import MCPServer
from mcp.types import INTERNAL_ERROR, ToolAnnotations
from pydantic import BaseModel, ConfigDict, Field

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
from agentic_lab.application.action_runtime import (
    ActionExecutionEvidence,
    GovernedActionExecutionError,
    GovernedActionRuntime,
)

_SERVER_NAME = "agentic-security-governed-actions"
_LOCAL_CALLER_ID = "local-mcp-host"
_FINDING_RESOURCE = "finding:demo-001"
_FAILURE_RESOURCE = "finding:missing"


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
_context = ActionContext(caller_id=_LOCAL_CALLER_ID)
_rules: dict[ActionAuthorizationRuleKey, AuthorizationOutcome] = {
    (
        _LOCAL_CALLER_ID,
        "trusted_composition",
        ACKNOWLEDGE_FINDING_ACTION,
        _FINDING_RESOURCE,
        "test",
    ): "allow",
    (
        _LOCAL_CALLER_ID,
        "trusted_composition",
        ACKNOWLEDGE_FINDING_ACTION,
        _FAILURE_RESOURCE,
        "test",
    ): "allow",
    (
        _LOCAL_CALLER_ID,
        "trusted_composition",
        ACKNOWLEDGE_FINDING_ACTION,
        _FINDING_RESOURCE,
        "staging",
    ): "deny",
    (
        _LOCAL_CALLER_ID,
        "trusted_composition",
        ACKNOWLEDGE_FINDING_ACTION,
        _FINDING_RESOURCE,
        "production",
    ): "require_human_approval",
}
_runtime = GovernedActionRuntime(
    authorizer=StaticActionAuthorizationPolicy(_rules),
    executor=_executor,
)


@mcp.tool(
    title="Acknowledge governed finding",
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
) -> ActionExecutionEvidence:
    """Route one model-controlled scope through application-owned enforcement."""
    proposed_action = ProposedAction(
        action=ACKNOWLEDGE_FINDING_ACTION,
        resource=resource,
        environment=environment,
    )
    try:
        return _runtime.execute(proposed_action, _context)
    except GovernedActionExecutionError as exc:
        raise MCPError(
            code=INTERNAL_ERROR,
            message="governed action execution outcome is unknown",
            data={
                "execution_failure": exc.evidence.model_dump(mode="json"),
            },
        ) from exc


@mcp.tool(
    title="Get governed finding acknowledgement state",
    annotations=ToolAnnotations(
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
def get_finding_acknowledgement_state() -> FindingAcknowledgementState:
    """Return observable local state independently from action execution evidence."""
    return FindingAcknowledgementState(
        resource=_FINDING_RESOURCE,
        acknowledged=_executor.is_acknowledged(_FINDING_RESOURCE),
        execution_count=_executor.execution_count,
    )


if __name__ == "__main__":
    mcp.run(transport="stdio")
