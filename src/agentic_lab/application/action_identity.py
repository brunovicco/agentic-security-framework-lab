"""Framework-neutral authentication boundary for governed action callers."""

from typing import Literal, Protocol, Self

from pydantic import BaseModel, ConfigDict, SecretStr, field_validator, model_validator

from agentic_lab.application.action_authorization import ActionContext

CallerAuthenticationOutcome = Literal["authenticated", "rejected"]
CallerAuthenticationReason = Literal["credential_verified", "credential_rejected"]


class CallerCredential(BaseModel):
    """Carry one opaque caller credential without exposing its raw value."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    secret: SecretStr

    @field_validator("secret")
    @classmethod
    def reject_empty_secret(cls, value: SecretStr) -> SecretStr:
        """Reject empty credentials before they reach an authentication adapter."""
        if not value.get_secret_value():
            raise ValueError("caller credential must not be empty")
        return value


class CallerAuthenticationDecision(BaseModel):
    """Represent credential verification without retaining credential material."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    outcome: CallerAuthenticationOutcome
    reason: CallerAuthenticationReason
    context: ActionContext | None = None

    @model_validator(mode="after")
    def validate_context_consistency(self) -> Self:
        """Bind trusted context presence to a successful authentication outcome."""
        if self.outcome == "authenticated":
            if self.reason != "credential_verified" or self.context is None:
                raise ValueError("authenticated decision requires verified caller context")
            return self

        if self.reason != "credential_rejected" or self.context is not None:
            raise ValueError("rejected decision cannot carry trusted caller context")
        return self


class CallerAuthenticator(Protocol):
    """Verify one opaque credential before creating trusted caller context."""

    def authenticate(self, credential: CallerCredential) -> CallerAuthenticationDecision:
        """Return a credential decision without exposing the credential itself."""
        ...
