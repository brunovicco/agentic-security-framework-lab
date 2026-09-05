"""Tests for framework-neutral governed action caller authentication contracts."""

import pytest
from pydantic import SecretStr, ValidationError

from agentic_lab.application.action_authorization import ActionContext
from agentic_lab.application.action_identity import (
    CallerAuthenticationDecision,
    CallerCredential,
)

RAW_CREDENTIAL = "svc_test_7fe7d3d0f62c4d1e8c59f1968a6a1f45"


def test_caller_credential_masks_secret_in_repr_and_json() -> None:
    """Keep raw service credentials out of routine object representations."""
    credential = CallerCredential(secret=SecretStr(RAW_CREDENTIAL))

    assert RAW_CREDENTIAL not in repr(credential)
    assert RAW_CREDENTIAL not in credential.model_dump_json()
    assert "**********" in credential.model_dump_json()


def test_empty_caller_credential_is_rejected() -> None:
    """Reject empty credential material before invoking an authentication adapter."""
    with pytest.raises(ValidationError, match="must not be empty"):
        CallerCredential(secret=SecretStr(""))


def test_authenticated_decision_requires_verified_context() -> None:
    """Require successful authentication to carry a trusted caller context."""
    context = ActionContext(caller_id="remediation-service", identity_source="api_key")

    decision = CallerAuthenticationDecision(
        outcome="authenticated",
        reason="credential_verified",
        context=context,
    )

    assert decision.context == context


@pytest.mark.parametrize(
    ("outcome", "reason", "context"),
    [
        ("authenticated", "credential_verified", None),
        (
            "authenticated",
            "credential_rejected",
            ActionContext(caller_id="remediation-service", identity_source="api_key"),
        ),
        (
            "rejected",
            "credential_rejected",
            ActionContext(caller_id="remediation-service", identity_source="api_key"),
        ),
        ("rejected", "credential_verified", None),
    ],
)
def test_authentication_decision_rejects_inconsistent_context(
    outcome: str,
    reason: str,
    context: ActionContext | None,
) -> None:
    """Prevent contradictory authentication evidence from being constructed."""
    with pytest.raises(ValidationError):
        CallerAuthenticationDecision.model_validate(
            {
                "outcome": outcome,
                "reason": reason,
                "context": context,
            }
        )
