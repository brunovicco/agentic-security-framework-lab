"""Framework-neutral deterministic authorization for proposed agent actions."""

from collections.abc import Mapping
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

AuthorizationOutcome = Literal[
    "allow",
    "deny",
    "require_human_approval",
]
AuthorizationReason = Literal[
    "explicit_allow",
    "explicit_deny",
    "human_approval_required",
    "no_matching_rule",
]

_REASON_BY_OUTCOME: dict[AuthorizationOutcome, AuthorizationReason] = {
    "allow": "explicit_allow",
    "deny": "explicit_deny",
    "require_human_approval": "human_approval_required",
}


class ProposedAction(BaseModel):
    """Represent an action proposed by an agent or other untrusted caller."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    action: str = Field(min_length=1)


class AuthorizationDecision(BaseModel):
    """Represent the deterministic authorization result for a proposed action."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    outcome: AuthorizationOutcome
    reason: AuthorizationReason


class ActionAuthorizer(Protocol):
    """Decide whether a proposed action is authorized to proceed."""

    def authorize(self, proposed_action: ProposedAction) -> AuthorizationDecision:
        """Return the deterministic authorization decision for one action."""
        ...


class StaticActionAuthorizationPolicy:
    """Authorize exact action identities from trusted static policy rules."""

    def __init__(self, rules: Mapping[str, AuthorizationOutcome]) -> None:
        """Copy trusted policy rules so later caller mutation cannot change policy."""
        self._rules = dict(rules)

    def authorize(self, proposed_action: ProposedAction) -> AuthorizationDecision:
        """Apply one exact-match rule or deny fail-closed when no rule exists."""
        outcome = self._rules.get(proposed_action.action)
        if outcome is None:
            return AuthorizationDecision(
                outcome="deny",
                reason="no_matching_rule",
            )

        return AuthorizationDecision(
            outcome=outcome,
            reason=_REASON_BY_OUTCOME[outcome],
        )
