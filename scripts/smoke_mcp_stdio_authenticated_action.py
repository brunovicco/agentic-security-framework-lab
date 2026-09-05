"""Prove host-injected authentication through a real MCP v2 STDIO subprocess."""

import asyncio
import json
import os
import secrets
from hashlib import sha256

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

_SERVER_NAME = "agentic-security-authenticated-governed-actions"
_MUTABLE_TOOL = "acknowledge_finding"
_STATE_TOOL = "get_finding_acknowledgement_state"
_FINDING_RESOURCE = "finding:demo-001"
_CALLER_ID = "local-api-key-client"
_IDENTITY_SOURCE = "api_key"
_CREDENTIAL_ENV = "AGENTIC_SECURITY_CALLER_API_KEY"
_VERIFICATION_DIGEST_ENV = "AGENTIC_SECURITY_ALLOWED_API_KEY_SHA256"


def _server_parameters(
    *,
    credential: str | None,
    verification_digest: str | None,
) -> StdioServerParameters:
    """Build one isolated server process with host-only authentication environment."""
    env = dict(os.environ)
    env.pop(_CREDENTIAL_ENV, None)
    env.pop(_VERIFICATION_DIGEST_ENV, None)
    env["PYTHONPATH"] = "src"
    if credential is not None:
        env[_CREDENTIAL_ENV] = credential
    if verification_digest is not None:
        env[_VERIFICATION_DIGEST_ENV] = verification_digest

    return StdioServerParameters(
        command="uvx",
        args=[
            "--from",
            "mcp[cli]==2.1.1",
            "mcp",
            "run",
            "scripts/mcp_authenticated_action_server.py",
        ],
        env=env,
    )


def _digest(value: str) -> str:
    """Return trusted host verification material for one generated credential."""
    return sha256(value.encode("utf-8")).hexdigest()


def _require_mapping(value: object, label: str) -> dict[str, object]:
    """Return one structured mapping or fail the transport smoke."""
    if not isinstance(value, dict):
        raise RuntimeError(f"{label} must be a structured object")
    return value


def _assert_state(payload: object, *, acknowledged: bool, execution_count: int) -> None:
    """Validate independently observable mutable state across STDIO."""
    state = _require_mapping(payload, "finding state")
    expected = {
        "resource": _FINDING_RESOURCE,
        "acknowledged": acknowledged,
        "execution_count": execution_count,
    }
    if state != expected:
        raise RuntimeError(f"Unexpected finding state: {state!r}")


def _assert_tool_schema(tools: object) -> None:
    """Require the model-visible mutable Tool to contain action scope only."""
    tool_list = getattr(tools, "tools", None)
    if not isinstance(tool_list, list):
        raise RuntimeError("Tool listing must expose a list")
    catalog = {tool.name: tool for tool in tool_list}
    if set(catalog) != {_MUTABLE_TOOL, _STATE_TOOL}:
        raise RuntimeError(f"Unexpected authenticated MCP Tool catalog: {sorted(catalog)}")
    properties = catalog[_MUTABLE_TOOL].input_schema.get("properties")
    if not isinstance(properties, dict):
        raise RuntimeError("Authenticated mutable Tool must expose object properties")
    if set(properties) != {"resource", "environment"}:
        raise RuntimeError("Host credential material leaked into model-controlled Tool schema")


def _assert_rejected_authentication(payload: object, credential: str) -> None:
    """Require invalid host credential to stop before authorization evidence exists."""
    document = _require_mapping(payload, "rejected authentication result")
    if credential in json.dumps(document, sort_keys=True):
        raise RuntimeError("Rejected host credential leaked into MCP evidence")
    authentication = _require_mapping(document.get("authentication"), "authentication evidence")
    expected = {
        "outcome": "rejected",
        "reason": "credential_rejected",
        "context": None,
    }
    if authentication != expected:
        raise RuntimeError(f"Unexpected rejected authentication evidence: {authentication!r}")
    if document.get("execution") is not None:
        raise RuntimeError(
            "Rejected authentication must not produce authorization/execution evidence"
        )


def _assert_authenticated_execution(
    payload: object,
    *,
    credential: str,
    environment: str,
    outcome: str,
    reason: str,
    approval_status: str,
    execution_occurred: bool,
) -> None:
    """Validate authentication and source-aware governed execution as separate evidence."""
    document = _require_mapping(payload, "authenticated action result")
    if credential in json.dumps(document, sort_keys=True):
        raise RuntimeError("Raw host credential leaked into MCP evidence")

    authentication = _require_mapping(document.get("authentication"), "authentication evidence")
    context = _require_mapping(authentication.get("context"), "authenticated context")
    expected_context = {
        "caller_id": _CALLER_ID,
        "identity_source": _IDENTITY_SOURCE,
    }
    if authentication.get("outcome") != "authenticated":
        raise RuntimeError(f"Unexpected authentication outcome: {authentication!r}")
    if authentication.get("reason") != "credential_verified":
        raise RuntimeError(f"Unexpected authentication reason: {authentication!r}")
    if context != expected_context:
        raise RuntimeError(f"Unexpected authenticated context: {context!r}")

    execution = _require_mapping(document.get("execution"), "execution evidence")
    if _require_mapping(execution.get("context"), "execution context") != expected_context:
        raise RuntimeError("Execution context diverged from authenticated identity")
    proposed_action = _require_mapping(execution.get("proposed_action"), "proposed action")
    expected_action = {
        "action": _MUTABLE_TOOL,
        "resource": _FINDING_RESOURCE,
        "environment": environment,
    }
    if proposed_action != expected_action:
        raise RuntimeError(f"Unexpected proposed action: {proposed_action!r}")
    authorization = _require_mapping(execution.get("authorization"), "authorization decision")
    if authorization != {"outcome": outcome, "reason": reason}:
        raise RuntimeError(f"Unexpected authorization decision: {authorization!r}")
    if execution.get("approval_status") != approval_status:
        raise RuntimeError(f"Unexpected approval status: {execution.get('approval_status')!r}")
    if execution.get("execution_occurred") is not execution_occurred:
        raise RuntimeError(f"Unexpected execution flag: {execution.get('execution_occurred')!r}")


async def _read_state(session: ClientSession) -> dict[str, object]:
    """Read observable state through the separate read-only Tool."""
    result = await session.call_tool(_STATE_TOOL, {})
    if result.is_error:
        raise RuntimeError(f"State Tool returned an error: {result.content}")
    return _require_mapping(result.structured_content, "state Tool result")


async def _call_action(
    session: ClientSession,
    *,
    environment: str,
) -> object:
    """Call the model-visible action Tool with scope only."""
    return await session.call_tool(
        _MUTABLE_TOOL,
        {"resource": _FINDING_RESOURCE, "environment": environment},
    )


async def _missing_credential_case() -> None:
    """Require absent host credential to become a Tool error with zero side effects."""
    parameters = _server_parameters(
        credential=None,
        verification_digest=_digest(secrets.token_urlsafe(32)),
    )
    async with (
        stdio_client(parameters) as (read_stream, write_stream),
        ClientSession(read_stream, write_stream) as session,
    ):
        await session.initialize()
        _assert_tool_schema(await session.list_tools())
        _assert_state(await _read_state(session), acknowledged=False, execution_count=0)
        result = await _call_action(session, environment="test")
        if not result.is_error:
            raise RuntimeError("Missing host credential must fail closed as a Tool error")
        _assert_state(await _read_state(session), acknowledged=False, execution_count=0)


async def _invalid_credential_case() -> None:
    """Require invalid host credential to return rejection evidence and zero mutation."""
    expected_credential = secrets.token_urlsafe(32)
    presented_credential = secrets.token_urlsafe(32)
    parameters = _server_parameters(
        credential=presented_credential,
        verification_digest=_digest(expected_credential),
    )
    async with (
        stdio_client(parameters) as (read_stream, write_stream),
        ClientSession(read_stream, write_stream) as session,
    ):
        await session.initialize()
        _assert_state(await _read_state(session), acknowledged=False, execution_count=0)
        result = await _call_action(session, environment="test")
        if result.is_error:
            raise RuntimeError(f"Invalid credential should return evidence: {result.content}")
        _assert_rejected_authentication(result.structured_content, presented_credential)
        _assert_state(await _read_state(session), acknowledged=False, execution_count=0)


async def _valid_credential_case() -> None:
    """Require valid host authentication before source-aware policy and mutation."""
    credential = secrets.token_urlsafe(32)
    parameters = _server_parameters(
        credential=credential,
        verification_digest=_digest(credential),
    )
    async with (
        stdio_client(parameters) as (read_stream, write_stream),
        ClientSession(read_stream, write_stream) as session,
    ):
        initialization = await session.initialize()
        if initialization.server_info.name != _SERVER_NAME:
            raise RuntimeError(f"Unexpected MCP server name: {initialization.server_info.name}")
        _assert_tool_schema(await session.list_tools())
        _assert_state(await _read_state(session), acknowledged=False, execution_count=0)

        denied = await _call_action(session, environment="staging")
        if denied.is_error:
            raise RuntimeError(f"Authorized identity deny should return evidence: {denied.content}")
        _assert_authenticated_execution(
            denied.structured_content,
            credential=credential,
            environment="staging",
            outcome="deny",
            reason="explicit_deny",
            approval_status="not_applicable",
            execution_occurred=False,
        )
        _assert_state(await _read_state(session), acknowledged=False, execution_count=0)

        approval_required = await _call_action(session, environment="production")
        if approval_required.is_error:
            raise RuntimeError(
                "Authenticated approval-required action should return evidence: "
                f"{approval_required.content}"
            )
        _assert_authenticated_execution(
            approval_required.structured_content,
            credential=credential,
            environment="production",
            outcome="require_human_approval",
            reason="human_approval_required",
            approval_status="missing",
            execution_occurred=False,
        )
        _assert_state(await _read_state(session), acknowledged=False, execution_count=0)

        allowed = await _call_action(session, environment="test")
        if allowed.is_error:
            raise RuntimeError(f"Authenticated allowed action returned error: {allowed.content}")
        _assert_authenticated_execution(
            allowed.structured_content,
            credential=credential,
            environment="test",
            outcome="allow",
            reason="explicit_allow",
            approval_status="not_applicable",
            execution_occurred=True,
        )
        _assert_state(await _read_state(session), acknowledged=True, execution_count=1)


async def _smoke() -> dict[str, object]:
    """Exercise missing, invalid, and valid host authentication through real STDIO."""
    await _missing_credential_case()
    await _invalid_credential_case()
    await _valid_credential_case()
    return {
        "type": "mcp_stdio_authenticated_action_smoke",
        "server": _SERVER_NAME,
        "transport": "stdio",
        "credential_in_tool_schema": False,
        "trusted_identity_source": _IDENTITY_SOURCE,
        "missing_credential_side_effects": 0,
        "invalid_credential_side_effects": 0,
        "valid_denied_side_effects": 0,
        "valid_approval_required_side_effects": 0,
        "valid_allowed_side_effects": 1,
    }


def main() -> None:
    """Run the provider-free host-authenticated MCP transport smoke."""
    print(json.dumps(asyncio.run(_smoke())))


if __name__ == "__main__":
    main()
