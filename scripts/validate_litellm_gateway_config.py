"""Validate the committed LiteLLM gateway foundation without provider access."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, cast

_CONFIG_PATH = Path("config/litellm/config.yaml")
_EXPECTED_ALIAS = "security-analysis"
_EXPECTED_UPSTREAM_MODEL = "openai/gpt-5.6-luna"
_EXPECTED_PROVIDER_KEY_REF = "os.environ/OPENAI_API_KEY"
_EXPECTED_MASTER_KEY_REF = "os.environ/LITELLM_MASTER_KEY"
_ENVIRONMENT_REFERENCE = re.compile(r"^os\.environ/[A-Z][A-Z0-9_]*$")


def _json_object(value: object, *, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{context} must be an object")
    return cast(dict[str, Any], value)


def _require_exact_keys(payload: dict[str, Any], expected: set[str], *, context: str) -> None:
    observed = set(payload)
    if observed != expected:
        missing = sorted(expected - observed)
        unexpected = sorted(observed - expected)
        details: list[str] = []
        if missing:
            details.append(f"missing={','.join(missing)}")
        if unexpected:
            details.append(f"unexpected={','.join(unexpected)}")
        raise ValueError(
            f"{context} keys do not match the accepted foundation: {'; '.join(details)}"
        )


def _require_environment_reference(value: object, *, context: str) -> str:
    if not isinstance(value, str) or not _ENVIRONMENT_REFERENCE.fullmatch(value):
        raise ValueError(f"{context} must reference an environment variable")
    return value


def validate_gateway_config(path: Path = _CONFIG_PATH) -> dict[str, Any]:
    """Validate the minimal LiteLLM gateway configuration and return its object."""
    payload = _json_object(json.loads(path.read_text()), context="gateway config")
    _require_exact_keys(payload, {"model_list", "general_settings"}, context="gateway config")

    model_list = payload["model_list"]
    if not isinstance(model_list, list) or len(model_list) != 1:
        raise ValueError("gateway foundation must expose exactly one model alias")

    model_entry = _json_object(model_list[0], context="model entry")
    _require_exact_keys(model_entry, {"model_name", "litellm_params"}, context="model entry")

    if model_entry["model_name"] != _EXPECTED_ALIAS:
        raise ValueError(f"gateway model alias must remain {_EXPECTED_ALIAS}")

    params = _json_object(model_entry["litellm_params"], context="litellm_params")
    _require_exact_keys(params, {"model", "api_key"}, context="litellm_params")

    if params["model"] != _EXPECTED_UPSTREAM_MODEL:
        raise ValueError(f"gateway upstream model must remain {_EXPECTED_UPSTREAM_MODEL}")

    provider_key_ref = _require_environment_reference(
        params["api_key"],
        context="provider api_key",
    )
    if provider_key_ref != _EXPECTED_PROVIDER_KEY_REF:
        raise ValueError(f"provider api_key must use {_EXPECTED_PROVIDER_KEY_REF}")

    general_settings = _json_object(payload["general_settings"], context="general_settings")
    _require_exact_keys(general_settings, {"master_key"}, context="general_settings")

    master_key_ref = _require_environment_reference(
        general_settings["master_key"],
        context="gateway master_key",
    )
    if master_key_ref != _EXPECTED_MASTER_KEY_REF:
        raise ValueError(f"gateway master_key must use {_EXPECTED_MASTER_KEY_REF}")

    return payload


def main() -> None:
    """Validate the repository gateway config as a standalone quality check."""
    payload = validate_gateway_config()
    model_entry = cast(dict[str, Any], cast(list[object], payload["model_list"])[0])
    params = cast(dict[str, Any], model_entry["litellm_params"])
    print(f"gateway_alias: {model_entry['model_name']}")
    print(f"upstream_model: {params['model']}")
    print("status: pass")


if __name__ == "__main__":
    main()
