"""Exercise governed mutable action semantics through the MCP v2 SDK in memory."""

import asyncio
import json

from mcp import Client
from mcp_governed_action_server import mcp

_MUTABLE_TOOL = "acknowledge_finding"
_STATE_TOOL = "get_finding_acknowledgement_state"
_FINDING_RESOURCE = "finding:demo-001"
_LOCAL_CALLER_ID = "local-mcp-host"


def _require_mapping(value: object, label: str) -> dict[str, object]:
    """Return one structured mapping or fail the compatibility check."""
    if not isinstance(value, dict):
        raise RuntimeError(f"{label} must be a structured object")
    return value


def _assert_execution(
    payload: object,
    *,
    outcome: str,
    reason: str,
    approval_status: str,
    execution_occurred: bool,
    resource: str = _FINDING_RESOURCE,
    environment: str,
) -> None:
    """Validate the application-owned execution evidence returned through MCP."""
    document = _require_mapping(payload, "governed action result")
    proposed_action = _require_mapping(document.get("proposed_action"), "proposed action")
    context = _require_mapping(document.get("context"), "action context")
    authorization = _require_mapping(document.get("authorization"), "authorization decision")

    expected_action = {
        "action": _MUTABLE_TOOL,
        "resource": resource,
        "environment": environment,
    }
    if proposed_action != expected_action:
        raise RuntimeError(f"Unexpected proposed action: {proposed_action!r}")
    if context != {"caller_id": _LOCAL_CALLER_ID}:
        raise RuntimeError(f"Unexpected trusted action context: {context!r}")
    if authorization != {"outcome": outcome, "reason": reason}:
        raise RuntimeError(f"Unexpected authorization decision: {authorization!r}")
    if document.get("approval_status") != approval_status:
        raise RuntimeError(f"Unexpected approval status: {document.get('approval_status')!r}")
    if document.get("execution_occurred") is not execution_occurred:
        raise RuntimeError(
            "Unexpected execution flag: " f"{document.get('execution_occurred')!r}"
        )


def _assert_state(payload: object, *, acknowledged: bool, execution_count: int) -> None:
    """Validate independently observable fixture state after one or more Tool calls."""
    document = _require_mapping(payload, "finding acknowledgement state")
    expected = {
        "resource": _FINDING_RESOURCE,
        "acknowledged": acknowledged,
        "execution_count": execution_count,
    }
    if document != expected:
        raise RuntimeError(f"Unexpected finding state: {document!r}")


async def _call_state(client: Client) -> dict[str, object]:
    """Read the independent state Tool and return its structured content."""
    result = await client.call_tool(_STATE_TOOL, {})
    if result.is_error:
        raise RuntimeError(f"State Tool returned an error: {result.content}")
    return _require_mapping(result.structured_content, "state Tool result")


async def _check() -> dict[str, object]:
    """Prove MCP discovery cannot bypass governed authorization or approval."""
    async with Client(mcp, raise_exceptions=True) as client:
        listing = await client.list_tools()
        tools = {tool.name: tool for tool in listing.tools}
        if set(tools) != {_MUTABLE_TOOL, _STATE_TOOL}:
            raise RuntimeError(f"Unexpected governed MCP Tool catalog: {sorted(tools)}")

        mutable = tools[_MUTABLE_TOOL]
        mutable_properties = mutable.input_schema.get("properties")
        if not isinstance(mutable_properties, dict):
            raise RuntimeError("Mutable Tool must expose an object input schema")
        if set(mutable_properties) != {"resource", "environment"}:
            raise RuntimeError(
                "Mutable Tool must accept only model-controlled resource and environment"
            )
        forbidden_arguments = {"action", "caller_id", "approval_id", "approver_id"}
        if forbidden_arguments.intersection(mutable_properties):
            raise RuntimeError("Trusted action authority leaked into MCP Tool arguments")

        annotations = mutable.annotations
        if annotations is None:
            raise RuntimeError("Mutable Tool must declare explicit behavior annotations")
        if annotations.read_only_hint is not False:
            raise RuntimeError("Mutable Tool must not claim to be read-only")
        if annotations.idempotent_hint is not False:
            raise RuntimeError("Mutable Tool must not claim idempotence")
        if annotations.open_world_hint is not False:
            raise RuntimeError("Synthetic mutable Tool must remain closed-world")

        _assert_state(await _call_state(client), acknowledged=False, execution_count=0)

        denied = await client.call_tool(
            _MUTABLE_TOOL,
            {"resource": _FINDING_RESOURCE, "environment": "staging"},
        )
        if denied.is_error:
            raise RuntimeError(f"Denied action should return evidence, not Tool error: {denied.content}")
        _assert_execution(
            denied.structured_content,
            outcome="deny",
            reason="explicit_deny",
            approval_status="not_applicable",
            execution_occurred=False,
            environment="staging",
        )
        _assert_state(await _call_state(client), acknowledged=False, execution_count=0)

        approval_required = await client.call_tool(
            _MUTABLE_TOOL,
            {"resource": _FINDING_RESOURCE, "environment": "production"},
        )
        if approval_required.is_error:
            raise RuntimeError(
                "Approval-required action should return evidence, not Tool error: "
                f"{approval_required.content}"
            )
        _assert_execution(
            approval_required.structured_content,
            outcome="require_human_approval",
            reason="human_approval_required",
            approval_status="missing",
            execution_occurred=False,
            environment="production",
        )
        _assert_state(await _call_state(client), acknowledged=False, execution_count=0)

        escalated = await client.call_tool(
            _MUTABLE_TOOL,
            {"resource": "finding:demo-999", "environment": "test"},
        )
        if escalated.is_error:
            raise RuntimeError(
                f"Scope escalation should return denial evidence, not Tool error: {escalated.content}"
            )
        _assert_execution(
            escalated.structured_content,
            outcome="deny",
            reason="no_matching_rule",
            approval_status="not_applicable",
            execution_occurred=False,
            resource="finding:demo-999",
            environment="test",
        )
        _assert_state(await _call_state(client), acknowledged=False, execution_count=0)

        allowed = await client.call_tool(
            _MUTABLE_TOOL,
            {"resource": _FINDING_RESOURCE, "environment": "test"},
        )
        if allowed.is_error:
            raise RuntimeError(f"Allowed action returned a Tool error: {allowed.content}")
        _assert_execution(
            allowed.structured_content,
            outcome="allow",
            reason="explicit_allow",
            approval_status="not_applicable",
            execution_occurred=True,
            environment="test",
        )
        _assert_state(await _call_state(client), acknowledged=True, execution_count=1)

        return {
            "type": "mcp_v2_governed_action_compatibility_check",
            "tool": _MUTABLE_TOOL,
            "state_tool": _STATE_TOOL,
            "trusted_context_in_tool_schema": False,
            "denied_side_effects": 0,
            "approval_required_side_effects": 0,
            "scope_escalation_side_effects": 0,
            "allowed_side_effects": 1,
        }


def main() -> None:
    """Run the isolated governed-action compatibility check."""
    print(json.dumps(asyncio.run(_check())))


if __name__ == "__main__":
    main()
