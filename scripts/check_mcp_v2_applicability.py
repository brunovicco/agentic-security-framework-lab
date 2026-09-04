"""Exercise the MCP v2 applicability server with the current SDK in memory."""

import asyncio
import json

from mcp import Client
from mcp_security_server import mcp

_TOOL_NAME = "assess_vulnerability_applicability"
_RESOURCE_URI = "security://contracts/applicability"


def _validate_contract_resource(payload: object) -> None:
    """Require resource content to describe the current strict application schemas."""
    if not isinstance(payload, dict):
        raise RuntimeError("Applicability contract resource must contain a JSON object")
    if payload.get("contract") != _TOOL_NAME:
        raise RuntimeError("Applicability contract resource identifies an unexpected contract")

    for key in ("vulnerability_input_schema", "asset_input_schema", "result_schema"):
        schema = payload.get(key)
        if not isinstance(schema, dict):
            raise RuntimeError(f"Applicability contract resource is missing {key}")
        if schema.get("type") != "object":
            raise RuntimeError(f"Applicability contract {key} must describe an object")
        if schema.get("additionalProperties") is not False:
            raise RuntimeError(f"Applicability contract {key} must remain closed to extra fields")
        if not isinstance(schema.get("properties"), dict):
            raise RuntimeError(f"Applicability contract {key} must expose field properties")


async def _check() -> dict[str, object]:
    """Exercise tool and resource primitives through the v2 client/server boundary."""
    async with Client(mcp, raise_exceptions=True) as client:
        tool_listing = await client.list_tools()
        tools = {tool.name: tool for tool in tool_listing.tools}
        if set(tools) != {_TOOL_NAME}:
            raise RuntimeError(f"Unexpected MCP tool catalog: {sorted(tools)}")

        resource_listing = await client.list_resources()
        resources = {str(resource.uri): resource for resource in resource_listing.resources}
        if set(resources) != {_RESOURCE_URI}:
            raise RuntimeError(f"Unexpected MCP resource catalog: {sorted(resources)}")
        resource = resources[_RESOURCE_URI]
        if resource.mime_type != "application/json":
            raise RuntimeError("Applicability contract resource must use application/json")

        resource_result = await client.read_resource(_RESOURCE_URI)
        if len(resource_result.contents) != 1:
            raise RuntimeError("Applicability contract resource must return exactly one content item")
        resource_text = getattr(resource_result.contents[0], "text", None)
        if not isinstance(resource_text, str):
            raise RuntimeError("Applicability contract resource must return text JSON content")
        _validate_contract_resource(json.loads(resource_text))

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
            "resource": _RESOURCE_URI,
            "resource_count": len(resources),
            "resource_contract_match": True,
            "read_only": annotations.read_only_hint,
            "closed_world": annotations.open_world_hint is False,
            "structured_output_match": True,
        }


def main() -> None:
    """Run the isolated compatibility check and emit a compact success record."""
    print(json.dumps(asyncio.run(_check())))


if __name__ == "__main__":
    main()
