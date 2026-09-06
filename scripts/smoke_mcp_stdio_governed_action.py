"""Prove governed mutable MCP execution through a real STDIO subprocess."""

import asyncio
import json
import os
import tomllib
from pathlib import Path

from mcp import ClientSession, MCPError, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import INTERNAL_ERROR

_CONFIG_PATH = Path(".codex/config.toml")
_SERVER_NAME = "agentic-security-governed-actions"
_MUTABLE_TOOL = "acknowledge_finding"
_STATE_TOOL = "get_finding_acknowledgement_state"
_FINDING_RESOURCE = "finding:demo-001"
_FAILURE_RESOURCE = "finding:missing"
_LOCAL_CALLER_ID = "local-mcp-host"
_LOCAL_IDENTITY_SOURCE = "trusted_composition"
_PROTOCOL_FAILURE_MESSAGE = "governed action execution outcome is unknown"
_RAW_EXECUTOR_ERROR = "finding does not exist"


def _load_server_parameters() -> StdioServerParameters:
    """Load the exact committed STDIO configuration for the governed action server."""
    with _CONFIG_PATH.open("rb") as handle:
        document = tomllib.load(handle)

    servers = document.get("mcp_servers")
    if not isinstance(servers, dict):
        raise RuntimeError("Project MCP config must define mcp_servers")
    server = servers.get(_SERVER_NAME)
    if not isinstance(server, dict):
        raise RuntimeError(f"Project MCP config must define {_SERVER_NAME!r}")

    command = server.get("command")
    args = server.get("args")
    env = server.get("env", {})
    if not isinstance(command, str) or not command:
        raise RuntimeError("Governed MCP server command must be a non-empty string")
    if not isinstance(args, list) or not all(isinstance(value, str) for value in args):
        raise RuntimeError("Governed MCP server args must be an array of strings")
    if not isinstance(env, dict) or not all(
        isinstance(key, str) and isinstance(value, str) for key, value in env.items()
    ):
        raise RuntimeError("Governed MCP server env must be a string mapping")

    return StdioServerParameters(
        command=command,
        args=args,
        env={**os.environ, **env},
    )


def _require_mapping(value: object, label: str) -> dict[str, object]:
    """Return one structured mapping or fail the transport smoke."""
    if not isinstance(value, dict):
        raise RuntimeError(f"{label} must be a structured object")
    return value


def _assert_state(payload: object, *, acknowledged: bool, execution_count: int) -> None:
    """Validate independently observable mutable state returned across STDIO."""
    state = _require_mapping(payload, "finding state")
    expected = {
        "resource": _FINDING_RESOURCE,
        "acknowledged": acknowledged,
        "execution_count": execution_count,
    }
    if state != expected:
        raise RuntimeError(f"Unexpected finding state: {state!r}")


def _assert_runtime_result(
    payload: object,
    *,
    outcome: str,
    approval_status: str,
    execution_occurred: bool,
) -> None:
    """Validate the governed runtime outcome and trusted caller source over MCP."""
    document = _require_mapping(payload, "governed execution result")
    context = _require_mapping(document.get("context"), "action context")
    expected_context = {
        "caller_id": _LOCAL_CALLER_ID,
        "identity_source": _LOCAL_IDENTITY_SOURCE,
    }
    if context != expected_context:
        raise RuntimeError(f"Unexpected trusted action context: {context!r}")

    authorization = _require_mapping(document.get("authorization"), "authorization decision")
    if authorization.get("outcome") != outcome:
        raise RuntimeError(f"Unexpected authorization outcome: {authorization!r}")
    if document.get("approval_status") != approval_status:
        raise RuntimeError(f"Unexpected approval status: {document.get('approval_status')!r}")
    if document.get("execution_occurred") is not execution_occurred:
        raise RuntimeError(f"Unexpected execution flag: {document.get('execution_occurred')!r}")


def _assert_uncertain_execution_protocol_error(error: MCPError) -> None:
    """Require host-only governed evidence for one uncertain mutable execution."""
    if error.error.code != INTERNAL_ERROR:
        raise RuntimeError(f"Unexpected uncertain-execution MCP code: {error.error.code!r}")
    if error.error.message != _PROTOCOL_FAILURE_MESSAGE:
        raise RuntimeError(f"Unexpected uncertain-execution MCP message: {error.error.message!r}")

    data = _require_mapping(error.error.data, "uncertain execution MCP data")
    serialized_data = json.dumps(data, sort_keys=True)
    if _RAW_EXECUTOR_ERROR in serialized_data:
        raise RuntimeError("Raw executor error leaked into uncertain-execution MCP data")

    execution_failure = _require_mapping(
        data.get("execution_failure"),
        "execution failure evidence",
    )
    expected_context = {
        "caller_id": _LOCAL_CALLER_ID,
        "identity_source": _LOCAL_IDENTITY_SOURCE,
    }
    if (
        _require_mapping(execution_failure.get("context"), "failure execution context")
        != expected_context
    ):
        raise RuntimeError("Failure execution context diverged from trusted identity")
    action = _require_mapping(execution_failure.get("proposed_action"), "failed action")
    expected_action = {
        "action": _MUTABLE_TOOL,
        "resource": _FAILURE_RESOURCE,
        "environment": "test",
    }
    if action != expected_action:
        raise RuntimeError(f"Unexpected failed action evidence: {action!r}")
    authorization = _require_mapping(
        execution_failure.get("authorization"),
        "failure authorization",
    )
    if authorization != {"outcome": "allow", "reason": "explicit_allow"}:
        raise RuntimeError(f"Unexpected failure authorization: {authorization!r}")
    if execution_failure.get("approval_status") != "not_applicable":
        raise RuntimeError("Direct governed failure unexpectedly carried HITL state")
    if execution_failure.get("execution_attempted") is not True:
        raise RuntimeError("Uncertain execution must record executor invocation")
    if execution_failure.get("external_side_effect_state") != "unknown":
        raise RuntimeError("Uncertain execution must preserve unknown side-effect state")
    if execution_failure.get("failure_reason") != "executor_error":
        raise RuntimeError("Uncertain execution must preserve executor_error reason")


async def _read_state(session: ClientSession) -> dict[str, object]:
    """Read observable action state through the separate read-only MCP Tool."""
    result = await session.call_tool(_STATE_TOOL, {})
    if result.is_error:
        raise RuntimeError(f"State Tool returned an error: {result.content}")
    return _require_mapping(result.structured_content, "state Tool result")


async def _call_action(
    session: ClientSession,
    *,
    resource: str,
    environment: str,
) -> dict[str, object]:
    """Call the mutable MCP Tool and return its structured runtime evidence."""
    result = await session.call_tool(
        _MUTABLE_TOOL,
        {"resource": resource, "environment": environment},
    )
    if result.is_error:
        raise RuntimeError(f"Governed action Tool returned an error: {result.content}")
    return _require_mapping(result.structured_content, "governed action Tool result")


async def _smoke() -> dict[str, object]:
    """Exercise governed mutable success, blocks, and uncertain failure over STDIO."""
    server_parameters = _load_server_parameters()

    async with (
        stdio_client(server_parameters) as (read_stream, write_stream),
        ClientSession(read_stream, write_stream) as session,
    ):
        initialization = await session.initialize()

        tools = await session.list_tools()
        tool_names = {tool.name for tool in tools.tools}
        if tool_names != {_MUTABLE_TOOL, _STATE_TOOL}:
            raise RuntimeError(f"Unexpected governed MCP Tool catalog: {sorted(tool_names)}")

        _assert_state(await _read_state(session), acknowledged=False, execution_count=0)

        denied = await _call_action(
            session,
            resource=_FINDING_RESOURCE,
            environment="staging",
        )
        _assert_runtime_result(
            denied,
            outcome="deny",
            approval_status="not_applicable",
            execution_occurred=False,
        )
        _assert_state(await _read_state(session), acknowledged=False, execution_count=0)

        approval_required = await _call_action(
            session,
            resource=_FINDING_RESOURCE,
            environment="production",
        )
        _assert_runtime_result(
            approval_required,
            outcome="require_human_approval",
            approval_status="missing",
            execution_occurred=False,
        )
        _assert_state(await _read_state(session), acknowledged=False, execution_count=0)

        escalated = await _call_action(
            session,
            resource="finding:demo-999",
            environment="test",
        )
        _assert_runtime_result(
            escalated,
            outcome="deny",
            approval_status="not_applicable",
            execution_occurred=False,
        )
        _assert_state(await _read_state(session), acknowledged=False, execution_count=0)

        try:
            uncertain = await session.call_tool(
                _MUTABLE_TOOL,
                {"resource": _FAILURE_RESOURCE, "environment": "test"},
            )
        except MCPError as exc:
            _assert_uncertain_execution_protocol_error(exc)
        else:
            raise RuntimeError(
                "Uncertain mutable execution must raise a host-only MCP protocol error; "
                f"received Tool result is_error={uncertain.is_error!r}"
            )
        _assert_state(await _read_state(session), acknowledged=False, execution_count=0)

        allowed = await _call_action(
            session,
            resource=_FINDING_RESOURCE,
            environment="test",
        )
        _assert_runtime_result(
            allowed,
            outcome="allow",
            approval_status="not_applicable",
            execution_occurred=True,
        )
        _assert_state(await _read_state(session), acknowledged=True, execution_count=1)

        return {
            "type": "mcp_stdio_governed_action_smoke",
            "server": _SERVER_NAME,
            "server_name": initialization.server_info.name,
            "transport": "stdio",
            "mutable_tool": _MUTABLE_TOOL,
            "state_tool": _STATE_TOOL,
            "trusted_identity_source": _LOCAL_IDENTITY_SOURCE,
            "blocked_mutations": 3,
            "uncertain_execution_protocol_error": True,
            "uncertain_execution_model_visible_tool_error": False,
            "uncertain_execution_observed_fixture_mutations": 0,
            "allowed_mutations": 1,
            "final_execution_count": 1,
        }


def main() -> None:
    """Run the provider-free governed MCP transport smoke."""
    print(json.dumps(asyncio.run(_smoke())))


if __name__ == "__main__":
    main()
