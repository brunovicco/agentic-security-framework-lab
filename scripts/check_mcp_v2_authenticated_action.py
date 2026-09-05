"""Exercise host-authenticated governed action semantics through the MCP v2 SDK."""

import asyncio
import json
import os
import secrets
from hashlib import sha256

from mcp import Client

_CREDENTIAL_ENV = "AGENTIC_SECURITY_CALLER_API_KEY"
_VERIFICATION_DIGEST_ENV = "AGENTIC_SECURITY_ALLOWED_API_KEY_SHA256"
_MUTABLE_TOOL = "acknowledge_finding"
_STATE_TOOL = "get_finding_acknowledgement_state"
_FINDING_RESOURCE = "finding:demo-001"
_CALLER_ID = "local-api-key-client"
_IDENTITY_SOURCE = "api_key"


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
            raise RuntimeError("Trusted authentication or authorization data leaked into Tool input")

        state = await client.call_tool(_STATE_TOOL, {})
        if state.is_error:
            raise RuntimeError(f"State Tool returned an error: {state.content}")
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
            raise RuntimeError("Execution context diverged from authenticated caller context")
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
            "execution_count": 1,
        }


def main() -> None:
    """Run the isolated host-authenticated MCP compatibility check."""
    print(json.dumps(asyncio.run(_check())))


if __name__ == "__main__":
    main()
