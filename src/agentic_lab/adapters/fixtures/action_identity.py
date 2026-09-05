"""Provider-free service credential authentication fixture for governed actions."""

from collections.abc import Mapping
from hashlib import sha256
from hmac import compare_digest

from agentic_lab.application.action_authorization import ActionContext
from agentic_lab.application.action_identity import (
    CallerAuthenticationDecision,
    CallerCredential,
)


class StaticApiKeyCallerAuthenticator:
    """Verify synthetic service API keys against copied SHA-256 credential digests."""

    def __init__(self, api_keys: Mapping[str, str]) -> None:
        """Reduce configured high-entropy API keys to digests and trusted caller ids."""
        records: list[tuple[bytes, str]] = []
        for api_key, caller_id in api_keys.items():
            if not api_key:
                raise ValueError("configured API key must not be empty")
            if not caller_id:
                raise ValueError("configured caller id must not be empty")
            records.append((self._digest(api_key), caller_id))
        self._records = tuple(records)

    @staticmethod
    def _digest(api_key: str) -> bytes:
        """Return a fixed-size digest for one synthetic high-entropy API key."""
        return sha256(api_key.encode("utf-8")).digest()

    def authenticate(self, credential: CallerCredential) -> CallerAuthenticationDecision:
        """Return trusted caller context only when one configured key digest matches."""
        presented_digest = self._digest(credential.secret.get_secret_value())
        matched_caller_id: str | None = None

        for expected_digest, caller_id in self._records:
            if compare_digest(presented_digest, expected_digest):
                matched_caller_id = caller_id

        if matched_caller_id is None:
            return CallerAuthenticationDecision(
                outcome="rejected",
                reason="credential_rejected",
            )

        return CallerAuthenticationDecision(
            outcome="authenticated",
            reason="credential_verified",
            context=ActionContext(
                caller_id=matched_caller_id,
                identity_source="api_key",
            ),
        )
