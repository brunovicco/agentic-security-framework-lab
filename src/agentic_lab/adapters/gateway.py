"""Shared client-facing configuration for the centralized LiteLLM gateway."""

import os

_GATEWAY_BASE_URL_ENV = "AGENTIC_LAB_GATEWAY_BASE_URL"
_GATEWAY_API_KEY_ENV = "AGENTIC_LAB_GATEWAY_API_KEY"
_GATEWAY_MODEL_ALIAS = "security-analysis"


def _required_environment_value(name: str) -> str:
    """Return a required non-blank gateway environment value."""
    value = os.environ.get(name)
    if value is None or not value.strip():
        raise RuntimeError(f"{name} must be configured for LiteLLM gateway access")
    return value


def gateway_model_alias() -> str:
    """Return the stable client-facing model alias exposed by the gateway."""
    return _GATEWAY_MODEL_ALIAS


def gateway_base_url() -> str:
    """Return the configured OpenAI-compatible gateway endpoint."""
    return _required_environment_value(_GATEWAY_BASE_URL_ENV)


def gateway_api_key() -> str:
    """Return the configured client credential for gateway access."""
    return _required_environment_value(_GATEWAY_API_KEY_ENV)
