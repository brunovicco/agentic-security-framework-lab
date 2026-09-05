"""Tests for the provider-free service caller authentication fixture."""

from hashlib import sha256

import pytest
from pydantic import SecretStr

from agentic_lab.adapters.fixtures.action_identity import StaticApiKeyCallerAuthenticator
from agentic_lab.application.action_identity import CallerCredential

API_KEY = "svc_test_7fe7d3d0f62c4d1e8c59f1968a6a1f45"
OTHER_API_KEY = "svc_test_3b8ce97ef10f4aad9a52235d3908b764"
CALLER_ID = "remediation-service"


def _credential(value: str) -> CallerCredential:
    return CallerCredential(secret=SecretStr(value))


def _digest_hex(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def test_matching_api_key_authenticates_service_caller() -> None:
    """Create trusted caller context only after exact credential verification."""
    authenticator = StaticApiKeyCallerAuthenticator({API_KEY: CALLER_ID})

    decision = authenticator.authenticate(_credential(API_KEY))

    assert decision.outcome == "authenticated"
    assert decision.reason == "credential_verified"
    assert decision.context is not None
    assert decision.context.caller_id == CALLER_ID
    assert decision.context.identity_source == "api_key"


def test_precomputed_sha256_digest_authenticates_matching_service_caller() -> None:
    """Accept trusted verification material without retaining expected plaintext keys."""
    authenticator = StaticApiKeyCallerAuthenticator.from_sha256_hex(
        {_digest_hex(API_KEY): CALLER_ID}
    )

    decision = authenticator.authenticate(_credential(API_KEY))

    assert decision.outcome == "authenticated"
    assert decision.context is not None
    assert decision.context.caller_id == CALLER_ID
    assert decision.context.identity_source == "api_key"
    assert API_KEY not in repr(vars(authenticator))


def test_unknown_api_key_is_rejected_without_trusted_context() -> None:
    """Fail authentication closed when the presented service credential is unknown."""
    authenticator = StaticApiKeyCallerAuthenticator({API_KEY: CALLER_ID})

    decision = authenticator.authenticate(_credential(OTHER_API_KEY))

    assert decision.outcome == "rejected"
    assert decision.reason == "credential_rejected"
    assert decision.context is None


def test_configured_api_key_is_not_retained_as_plaintext() -> None:
    """Reduce configured credential material to fixed-size digests after construction."""
    authenticator = StaticApiKeyCallerAuthenticator({API_KEY: CALLER_ID})

    assert API_KEY not in repr(vars(authenticator))


@pytest.mark.parametrize(
    "configuration",
    [
        {"": CALLER_ID},
        {API_KEY: ""},
    ],
)
def test_invalid_authenticator_configuration_is_rejected(
    configuration: dict[str, str],
) -> None:
    """Reject empty credential or caller identifiers in trusted fixture configuration."""
    with pytest.raises(ValueError):
        StaticApiKeyCallerAuthenticator(configuration)


@pytest.mark.parametrize(
    "configuration",
    [
        {"": CALLER_ID},
        {"not-hex": CALLER_ID},
        {"00": CALLER_ID},
        {_digest_hex(API_KEY): ""},
    ],
)
def test_invalid_digest_configuration_is_rejected(
    configuration: dict[str, str],
) -> None:
    """Reject malformed verification digests before authentication can begin."""
    with pytest.raises(ValueError):
        StaticApiKeyCallerAuthenticator.from_sha256_hex(configuration)
