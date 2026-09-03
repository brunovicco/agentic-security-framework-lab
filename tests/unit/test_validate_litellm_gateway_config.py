"""Provider-free tests for the LiteLLM gateway foundation config."""

import json
from pathlib import Path
from runpy import run_path
from typing import Any

import pytest

_REPO_ROOT = Path(__file__).parents[2]
_SCRIPT = run_path(str(_REPO_ROOT / "scripts" / "validate_litellm_gateway_config.py"))
validate_gateway_config: Any = _SCRIPT["validate_gateway_config"]
_CONFIG = _REPO_ROOT / "config" / "litellm" / "config.yaml"


def _copy_config(tmp_path: Path) -> Path:
    target = tmp_path / "config.yaml"
    target.write_bytes(_CONFIG.read_bytes())
    return target


def test_gateway_foundation_config_is_valid() -> None:
    payload = validate_gateway_config(_CONFIG)

    assert payload["model_list"][0]["model_name"] == "security-analysis"
    assert payload["model_list"][0]["litellm_params"]["model"] == "openai/gpt-5.6-luna"
    assert payload["general_settings"]["master_key"] == "os.environ/LITELLM_MASTER_KEY"


def test_gateway_config_rejects_literal_provider_key(tmp_path: Path) -> None:
    path = _copy_config(tmp_path)
    payload = json.loads(path.read_text())
    payload["model_list"][0]["litellm_params"]["api_key"] = "sk-literal-secret"
    path.write_text(json.dumps(payload, indent=2) + "\n")

    with pytest.raises(ValueError, match="provider api_key must reference an environment variable"):
        validate_gateway_config(path)


def test_gateway_config_rejects_literal_master_key(tmp_path: Path) -> None:
    path = _copy_config(tmp_path)
    payload = json.loads(path.read_text())
    payload["general_settings"]["master_key"] = "sk-literal-admin-secret"
    path.write_text(json.dumps(payload, indent=2) + "\n")

    with pytest.raises(ValueError, match="gateway master_key must reference an environment variable"):
        validate_gateway_config(path)


def test_gateway_config_rejects_alias_drift(tmp_path: Path) -> None:
    path = _copy_config(tmp_path)
    payload = json.loads(path.read_text())
    payload["model_list"][0]["model_name"] = "arbitrary-provider-model"
    path.write_text(json.dumps(payload, indent=2) + "\n")

    with pytest.raises(ValueError, match="gateway model alias must remain security-analysis"):
        validate_gateway_config(path)


def test_gateway_config_rejects_upstream_model_drift(tmp_path: Path) -> None:
    path = _copy_config(tmp_path)
    payload = json.loads(path.read_text())
    payload["model_list"][0]["litellm_params"]["model"] = "anthropic/other-model"
    path.write_text(json.dumps(payload, indent=2) + "\n")

    with pytest.raises(ValueError, match="gateway upstream model must remain openai/gpt-5.6-luna"):
        validate_gateway_config(path)


def test_gateway_config_rejects_unreviewed_top_level_settings(tmp_path: Path) -> None:
    path = _copy_config(tmp_path)
    payload = json.loads(path.read_text())
    payload["router_settings"] = {"fallbacks": []}
    path.write_text(json.dumps(payload, indent=2) + "\n")

    with pytest.raises(ValueError, match="gateway config keys do not match"):
        validate_gateway_config(path)
