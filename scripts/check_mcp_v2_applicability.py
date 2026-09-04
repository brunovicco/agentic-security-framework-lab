"""Exercise the MCP v2 applicability server with the current SDK in memory."""

import asyncio
import json

from mcp import Client

from mcp_security_server import mcp

_TOOL_NAME = "assess_vulnerability_applicability"


async def _check() -> dict[str, object]:
    """List and call the first MCP tool through the v2 client/server boundary."""
    async with Client(mcp, raise_exceptions=True) as client:
        listing = await client.list_tools()
        tools = {tool.name: tool for tool in listing.tools}
        if set(tools) != {_TOOL_NAME}:
            raise RuntimeError(f"Unexpected MCP tool catalog: {sorted(tools)}")

        tool = tools[_TOOL_NAME]
        annotations = tool.annotations
        if annotations is None:
            raise RuntimeError("Applicability tool must declare explicit safety annotations")
        if annotations.read_only_hint is not True:
            raise RuntimeError("Applicability tool must be annotated read-only")
        if annotations.destructive_hint is not False:
            raise RuntimeError("Applicability tool must be annotated non-destructive")
        if annotations.idempotent_hint is not True:
            raise RuntimeError("Applicability tool must be annotated idempotent")
        if annotations.open_world_hint is not False:
            raise RuntimeError("Applicability tool must be annotated closed-world")

        result = await client.call_tool(
            _TOOL_NAME,
            {
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
            },
        )
        if result.is_error:
            raise RuntimeError(f"MCP applicability tool returned an error: {result.content}")

        expected = {
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
        if result.structured_content != expected:
            raise RuntimeError(
                "MCP structured output did not match deterministic application truth: "
                f"{result.structured_content!r}"
            )

        return {
            "type": "mcp_v2_compatibility_check",
            "tool": _TOOL_NAME,
            "tool_count": len(tools),
            "read_only": annotations.read_only_hint,
            "closed_world": annotations.open_world_hint is False,
            "structured_output_match": True,
        }


def main() -> None:
    """Run the isolated compatibility check and emit a compact success record."""
    print(json.dumps(asyncio.run(_check())))


if __name__ == "__main__":
    main()
