"""Exercise host-authenticated governed action semantics through the MCP v2 SDK."""

import asyncio
import json
import os
import secrets
from hashlib import sha256

from mcp import Client, MCPError
from mcp.types import INTERNAL_ERROR

_CREDENTIAL_ENV = "AGENTIC_SECURITY_CALLER_API_KEY"
_VERIFICATION_DIGEST_ENV = "AGENTIC_SECURITY_ALLOWED_API_KEY_SHA256"
_MUTABLE_TOOL = "acknowledge_finding"
_STATE_TOOL = "get_finding_acknowledgement_state"
_FINDING_RESOURCE = "finding:demo-001"
_FAILURE_RESOURCE = "finding:missing"
_CALLER_ID = "local-api-key-client"
_IDENTITY_SOURCE = "api_key"
_PROTOCOL_FAILURE_MESSAGE = "governed action execution outcome is unknown"
_RAW_EXECUTOR_ERROR = "finding does not exist"


def _require_mapping(value: object, label: str) -> dict[str, object]:
    """Return one structured mapping or fail the compatibility check."""
    if not isinstance(value, dict):
        raise RuntimeError(f"{label} must be a structured object")
    return value


def _assert_state(payload: object, *, acknowledged: bool, execution_count: int) -> None:
    """Validate independently observable fixture state."""
    state = _require_mapping(payload, "finding state")
    expected = {
        "resource": _FINDING_RESOURCE,
        "acknowledged": acknowledged,
        "execution_count": execution_count,
    }
    if state != expected:
        raise RuntimeError(f"Unexpected finding state: {state!r}")


def _assert_uncertain_execution_protocol_error(error: MCPError, credential: str) -> None:
    """Require safe host-only evidence for one post-executor uncertain outcome."""
    if error.error.code != INTERNAL_ERROR:
        raise RuntimeError(f"Unexpected MCP error code: {error.error.code!r}")
    if error.error.message != _PROTOCOL_FAILURE_MESSAGE:
        raise RuntimeError(f"Unexpected MCP error message: {error.error.message!r}")

    data = _require_mapping(error.error.data, "MCP protocol error data")
    serialized_data = json.dumps(data, sort_keys=True)
    if credential in serialized_data:
        raise RuntimeError("Raw host credential leaked into MCP protocol failure data")
    if _RAW_EXECUTOR_ERROR in serialized_data:
        raise RuntimeError("Raw executor error leaked into MCP protocol failure data")

    failure = _require_mapping(
        data.get("authenticated_execution_failure"),
        "authenticated execution failure",
    )
    authentication = _require_mapping(failure.get("authentication"), "authentication evidence")
    expected_context = {
        "caller_id": _CALLER_ID,
        "identity_source": _IDENTITY_SOURCE,
    }
    if authentication.get("outcome") != "authenticated":
        raise RuntimeError(f"Unexpected failure authentication outcome: {authentication!r}")
    if authentication.get("reason") != "credential_verified":
        raise RuntimeError(f"Unexpected failure authentication reason: {authentication!r}")
    if _require_mapping(authentication.get("context"), "authenticated context") != expected_context:
        raise RuntimeError("Failure authentication context diverged from trusted identity")

    execution_failure = _require_mapping(
        failure.get("execution_failure"),
        "governed execution failure",
    )
    if _require_mapping(execution_failure.get("context"), "failure context") != expected_context:
        raise RuntimeError("Failure execution context diverged from authenticated identity")
    proposed_action = _require_mapping(
        execution_failure.get("proposed_action"),
        "failed proposed action",
    )
    expected_action = {
        "action": _MUTABLE_TOOL,
        "resource": _FAILURE_RESOURCE,
        "environment": "test",
    }
    if proposed_action != expected_action:
        raise RuntimeError(f"Unexpected failed proposed action: {proposed_action!r}")
    authorization = _require_mapping(
        execution_failure.get("authorization"),
        "failure authorization",
    )
    if authorization != {"outcome": "allow", "reason": "explicit_allow"}:
        raise RuntimeError(f"Unexpected failure authorization: {authorization!r}")
    if execution_failure.get("approval_status") != "not_applicable":
        raise RuntimeError("Direct authenticated failure unexpectedly carried HITL state")
    if execution_failure.get("execution_attempted") is not True:
        raise RuntimeError("MCP failure evidence must record executor invocation")
    if execution_failure.get("external_side_effect_state") != "unknown":
        raise RuntimeError("MCP failure evidence must preserve unknown side-effect state")
    if execution_failure.get("failure_reason") != "executor_error":
        raise RuntimeError("MCP failure evidence must preserve closed executor failure reason")


async def _check() -> dict[str, object]:
    """Prove host credential authentication without credential-bearing Tool input."""
    credential = secrets.token_urlsafe(32)
    os.environ[_CREDENTIAL_ENV] = credential
    os.environ[_VERIFICATION_DIGEST_ENV] = sha256(credential.encode("utf-8")).hexdigest()

    from mcp_authenticated_action_server import mcp

    async with Client(mcp, raise_exceptions=True) as client:
        listing = await client.list_tools()
        tools = {tool.name: tool for tool in listing.tools}
        if set(tools) != {_MUTABLE_TOOL, _STATE_TOOL}:
            raise RuntimeError(f"Unexpected authenticated MCP Tool catalog: {sorted(tools)}")

        mutable = tools[_MUTABLE_TOOL]
        properties = mutable.input_schema.get("properties")
        if not isinstance(properties, dict):
            raise RuntimeError("Mutable Tool must expose an object input schema")
        if set(properties) != {"resource", "environment"}:
            raise RuntimeError(
                "Authenticated mutable Tool must accept only resource and environment"
            )
        forbidden = {
            "action",
            "caller_id",
            "identity_source",
            "credential",
            "api_key",
            "approval_id",
            "approver_id",
        }
        if forbidden.intersection(properties):
            raise RuntimeError(
                "Trusted authentication or authorization data leaked into Tool input"
            )

        state = await client.call_tool(_STATE_TOOL, {})
        if state.is_error:
            raise RuntimeError(f"State Tool returned an error: {state.content}")
        _assert_state(state.structured_content, acknowledged=False, execution_count=0)

        try:
            uncertain = await client.call_tool(
                _MUTABLE_TOOL,
                {"resource": _FAILURE_RESOURCE, "environment": "test"},
            )
        except MCPError as exc:
            _assert_uncertain_execution_protocol_error(exc, credential)
        else:
            raise RuntimeError(
                "Uncertain mutable execution must raise a host-only MCP protocol error; "
                f"received Tool result is_error={uncertain.is_error!r}"
            )

        state = await client.call_tool(_STATE_TOOL, {})
        if state.is_error:
            raise RuntimeError(f"State Tool returned an error after failure: {state.content}")
        _assert_state(state.structured_content, acknowledged=False, execution_count=0)

        result = await client.call_tool(
            _MUTABLE_TOOL,
            {"resource": _FINDING_RESOURCE, "environment": "test"},
        )
        if result.is_error:
            raise RuntimeError(f"Authenticated action returned a Tool error: {result.content}")
        document = _require_mapping(result.structured_content, "authenticated action result")
        if credential in json.dumps(document, sort_keys=True):
            raise RuntimeError("Raw host credential leaked into MCP execution evidence")

        authentication = _require_mapping(document.get("authentication"), "authentication evidence")
        if authentication.get("outcome") != "authenticated":
            raise RuntimeError(f"Unexpected authentication evidence: {authentication!r}")
        context = _require_mapping(authentication.get("context"), "authenticated context")
        expected_context = {
            "caller_id": _CALLER_ID,
            "identity_source": _IDENTITY_SOURCE,
        }
        if context != expected_context:
            raise RuntimeError(f"Unexpected authenticated context: {context!r}")

        execution = _require_mapping(document.get("execution"), "execution evidence")
        if _require_mapping(execution.get("context"), "execution context") != expected_context:
            raise RuntimeError("Execution context diverged from authenticated identity")
        authorization = _require_mapping(execution.get("authorization"), "authorization decision")
        if authorization != {"outcome": "allow", "reason": "explicit_allow"}:
            raise RuntimeError(f"Unexpected source-aware authorization: {authorization!r}")
        if execution.get("execution_occurred") is not True:
            raise RuntimeError("Authenticated allowed action did not execute")

        if _CREDENTIAL_ENV in os.environ:
            raise RuntimeError("Server did not remove captured credential from process environment")

        state = await client.call_tool(_STATE_TOOL, {})
        if state.is_error:
            raise RuntimeError(f"State Tool returned an error after execution: {state.content}")
        _assert_state(state.structured_content, acknowledged=True, execution_count=1)

        return {
            "type": "mcp_v2_authenticated_action_compatibility_check",
            "tool": _MUTABLE_TOOL,
            "state_tool": _STATE_TOOL,
            "credential_in_tool_schema": False,
            "credential_in_evidence": False,
            "trusted_identity_source": _IDENTITY_SOURCE,
            "uncertain_execution_protocol_error": True,
            "uncertain_execution_model_visible_tool_error": False,
            "uncertain_execution_side_effect_state": "unknown",
            "execution_count": 1,
        }


def main() -> None:
    """Run the isolated host-authenticated MCP compatibility check."""
    print(json.dumps(asyncio.run(_check())))


if __name__ == "__main__":
    main()
