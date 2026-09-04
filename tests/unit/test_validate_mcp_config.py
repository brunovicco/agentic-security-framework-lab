"""Provider-free tests for project-scoped MCP configuration and isolation."""

import tomllib
from pathlib import Path
from runpy import run_path
from typing import Any

import pytest

_ROOT = Path(__file__).parents[2]
_CONFIG_PATH = _ROOT / ".codex" / "config.toml"
_SERVER_PATH = _ROOT / "scripts" / "mcp_security_server.py"
_SCRIPT: dict[str, Any] = run_path(str(_ROOT / "scripts" / "validate_mcp_config.py"))
validate_runner: Any = _SCRIPT["validate_runner"]
validate_server: Any = _SCRIPT["validate_server"]


def test_uvx_runner_accepts_exactly_pinned_package_with_cli_extra() -> None:
    errors = validate_runner(
        _CONFIG_PATH,
        "agentic-security-applicability",
        "uvx",
        ["--from", "mcp[cli]==2.1.1", "mcp", "run", "scripts/mcp_security_server.py"],
    )

    assert errors == []


@pytest.mark.parametrize(
    "package",
    (
        "mcp[cli]",
        "mcp[cli]>=2.1.1",
        "mcp[cli]==2.1",
        "mcp[cli]==latest",
    ),
)
def test_uvx_runner_rejects_unpinned_or_inexact_cli_package(package: str) -> None:
    errors = validate_runner(
        _CONFIG_PATH,
        "agentic-security-applicability",
        "uvx",
        ["--from", package, "mcp", "run", "scripts/mcp_security_server.py"],
    )

    assert len(errors) == 1
    assert "exact == version" in errors[0]


def test_checked_in_mcp_server_configuration_passes_security_validation() -> None:
    with _CONFIG_PATH.open("rb") as handle:
        document = tomllib.load(handle)

    servers = document["mcp_servers"]
    config = servers["agentic-security-applicability"]

    assert validate_server(_CONFIG_PATH, "agentic-security-applicability", config) == []
    assert config["command"] == "uvx"
    assert config["args"][:2] == ["--from", "mcp[cli]==2.1.1"]
    assert config["env"] == {"PYTHONPATH": "src"}
    assert "env_vars" not in config


def test_mcp_server_is_a_thin_closed_world_protocol_adapter() -> None:
    source = _SERVER_PATH.read_text()

    assert "from mcp.server import MCPServer" in source
    assert "from mcp.types import ToolAnnotations" in source
    assert "read_only_hint=True" in source
    assert "destructive_hint=False" in source
    assert "idempotent_hint=True" in source
    assert "open_world_hint=False" in source
    assert "assess_applicability(" in source
    assert "openai" not in source.lower()
    assert "httpx" not in source.lower()
    assert "requests" not in source.lower()
