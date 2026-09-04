"""Prove the committed MCP host/client boundary over a real STDIO subprocess."""

import asyncio
import json
import os
import tomllib
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

_CONFIG_PATH = Path(".codex/config.toml")
_SERVER_NAME = "agentic-security-applicability"
_PROMPT_NAME = "review_vulnerability_applicability"
_RESOURCE_URI = "security://contracts/applicability"
_TOOL_NAME = "assess_vulnerability_applicability"


def _load_server_parameters() -> StdioServerParameters:
    """Load the exact committed STDIO server configuration used by the project host."""
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
        raise RuntimeError("MCP STDIO server command must be a non-empty string")
    if not isinstance(args, list) or not all(isinstance(value, str) for value in args):
        raise RuntimeError("MCP STDIO server args must be an array of strings")
    if not isinstance(env, dict) or not all(
        isinstance(key, str) and isinstance(value, str) for key, value in env.items()
    ):
        raise RuntimeError("MCP STDIO server env must be a string mapping")

    return StdioServerParameters(
        command=command,
        args=args,
        env={**os.environ, **env},
    )


def _tool_arguments() -> dict[str, object]:
    """Return deterministic structured evidence for the transport smoke."""
    return {
        "vulnerability": {
            "cve_id": "CVE-2026-9001",
            "product": "ExampleServer",
            "affected_before": "4.2",
            "severity": "critical",
            "cvss_score": "9.8",
            "epss_score": "0.91",
            "kev_listed": True,
        },
        "assets": [
            {
                "asset_id": "api-prod-01",
                "product": "ExampleServer",
                "version": "4.1",
                "environment": "production",
                "network_exposure": "internet-exposed",
            },
            {
                "asset_id": "api-prod-02",
                "product": "OtherServer",
                "version": "4.1",
                "environment": "production",
                "network_exposure": "internal",
            },
        ],
    }


def _expected_tool_output() -> dict[str, object]:
    """Return external expected truth for the deterministic smoke input."""
    return {
        "cve_id": "CVE-2026-9001",
        "assessments": [
            {
                "asset_id": "api-prod-01",
                "status": "affected",
                "rationale": "Installed version 4.1 is below 4.2.",
            },
            {
                "asset_id": "api-prod-02",
                "status": "not_applicable",
                "rationale": "Installed product does not match the vulnerable product.",
            },
        ],
    }


async def _smoke() -> dict[str, object]:
    """Launch the configured server and exercise MCP primitives through STDIO."""
    server_parameters = _load_server_parameters()

    async with stdio_client(server_parameters) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            initialization = await session.initialize()

            prompts = await session.list_prompts()
            prompt_names = {prompt.name for prompt in prompts.prompts}
            if prompt_names != {_PROMPT_NAME}:
                raise RuntimeError(f"Unexpected MCP prompt catalog: {sorted(prompt_names)}")

            prompt = await session.get_prompt(_PROMPT_NAME)
            if len(prompt.messages) != 1 or prompt.messages[0].role != "user":
                raise RuntimeError("MCP review prompt must return exactly one user message")

            resources = await session.list_resources()
            resource_uris = {str(resource.uri) for resource in resources.resources}
            if resource_uris != {_RESOURCE_URI}:
                raise RuntimeError(f"Unexpected MCP resource catalog: {sorted(resource_uris)}")

            resource = await session.read_resource(_RESOURCE_URI)
            if len(resource.contents) != 1:
                raise RuntimeError("MCP applicability resource must return exactly one content item")

            tools = await session.list_tools()
            tool_names = {tool.name for tool in tools.tools}
            if tool_names != {_TOOL_NAME}:
                raise RuntimeError(f"Unexpected MCP tool catalog: {sorted(tool_names)}")

            result = await session.call_tool(_TOOL_NAME, _tool_arguments())
            if result.is_error:
                raise RuntimeError(f"MCP applicability tool returned an error: {result.content}")
            if result.structured_content != _expected_tool_output():
                raise RuntimeError(
                    "MCP STDIO structured output did not match deterministic application truth"
                )

            return {
                "type": "mcp_stdio_host_client_smoke",
                "server": _SERVER_NAME,
                "server_name": initialization.server_info.name,
                "transport": "stdio",
                "prompt": _PROMPT_NAME,
                "resource": _RESOURCE_URI,
                "tool": _TOOL_NAME,
                "structured_output_match": True,
            }


def main() -> None:
    """Run the provider-free transport smoke and print compact non-secret evidence."""
    print(json.dumps(asyncio.run(_smoke())))


if __name__ == "__main__":
    main()
