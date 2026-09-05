"""Compose caller authentication with governed action execution."""

from typing import Self

from pydantic import BaseModel, ConfigDict, model_validator

from agentic_lab.application.action_authorization import ProposedAction
from agentic_lab.application.action_identity import (
    CallerAuthenticationDecision,
    CallerAuthenticator,
    CallerCredential,
)
from agentic_lab.application.action_runtime import ActionExecutionEvidence, GovernedActionRuntime


class AuthenticatedActionExecutionEvidence(BaseModel):
    """Record authentication separately from governed action execution evidence."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    authentication: CallerAuthenticationDecision
    execution: ActionExecutionEvidence | None = None

    @model_validator(mode="after")
    def validate_execution_consistency(self) -> Self:
        """Bind execution evidence to the exact context established by authentication."""
        if self.authentication.outcome == "rejected":
            if self.execution is not None:
                raise ValueError("rejected authentication cannot carry execution evidence")
            return self

        context = self.authentication.context
        if context is None or self.execution is None:
            raise ValueError("authenticated action requires execution evidence")
        if self.execution.context != context:
            raise ValueError("execution context must match authenticated caller context")
        return self


class AuthenticatedGovernedActionRuntime:
    """Authenticate a caller before delegating authorization and execution."""

    def __init__(
        self,
        authenticator: CallerAuthenticator,
        action_runtime: GovernedActionRuntime,
    ) -> None:
        """Bind independent authentication and governed-execution boundaries."""
        self._authenticator = authenticator
        self._action_runtime = action_runtime

    def execute(
        self,
        proposed_action: ProposedAction,
        credential: CallerCredential,
    ) -> AuthenticatedActionExecutionEvidence:
        """Authenticate first and invoke the governed runtime only on success."""
        authentication = self._authenticator.authenticate(credential)
        context = authentication.context
        if context is None:
            return AuthenticatedActionExecutionEvidence(authentication=authentication)

        execution = self._action_runtime.execute(proposed_action, context)
        return AuthenticatedActionExecutionEvidence(
            authentication=authentication,
            execution=execution,
        )
