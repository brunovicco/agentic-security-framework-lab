"""Framework-neutral deterministic authorization for proposed agent actions."""

from collections.abc import Mapping
from typing import Literal, Protocol, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

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
CallerIdentitySource = Literal["trusted_composition", "api_key"]
ActionAuthorizationRuleKey = tuple[str, CallerIdentitySource, str, str, str]

_REASON_BY_OUTCOME: dict[AuthorizationOutcome, AuthorizationReason] = {
    "allow": "explicit_allow",
    "deny": "explicit_deny",
    "require_human_approval": "human_approval_required",
}


class ProposedAction(BaseModel):
    """Represent a scoped action proposed by an agent or other untrusted caller."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    action: str = Field(min_length=1)
    resource: str = Field(min_length=1)
    environment: str = Field(min_length=1)


class ActionContext(BaseModel):
    """Carry trusted caller identity and its established identity source."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    caller_id: str = Field(min_length=1)
    identity_source: CallerIdentitySource = "trusted_composition"


class AuthorizationDecision(BaseModel):
    """Represent the deterministic authorization result for a proposed action."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    outcome: AuthorizationOutcome
    reason: AuthorizationReason

    @model_validator(mode="after")
    def validate_reason_consistency(self) -> Self:
        """Reject authorization outcome/reason pairs the policy cannot legally emit."""
        if self.outcome == "allow":
            if self.reason != "explicit_allow":
                raise ValueError("allow authorization requires explicit_allow reason")
            return self

        if self.outcome == "require_human_approval":
            if self.reason != "human_approval_required":
                raise ValueError(
                    "require_human_approval authorization requires human_approval_required reason"
                )
            return self

        if self.reason not in {"explicit_deny", "no_matching_rule"}:
            raise ValueError("deny authorization requires explicit_deny or no_matching_rule reason")
        return self


class ActionAuthorizer(Protocol):
    """Decide whether a proposed action is authorized to proceed."""

    def authorize(
        self,
        proposed_action: ProposedAction,
        context: ActionContext,
    ) -> AuthorizationDecision:
        """Return the deterministic authorization decision for one trusted caller."""
        ...


class StaticActionAuthorizationPolicy:
    """Authorize exact caller/source/action/resource/environment scopes from trusted rules."""

    def __init__(
        self,
        rules: Mapping[ActionAuthorizationRuleKey, AuthorizationOutcome],
    ) -> None:
        """Copy trusted policy rules so later caller mutation cannot change policy."""
        self._rules = dict(rules)

    def authorize(
        self,
        proposed_action: ProposedAction,
        context: ActionContext,
    ) -> AuthorizationDecision:
        """Apply one exact-scope rule or deny fail-closed when no rule exists."""
        policy_key: ActionAuthorizationRuleKey = (
            context.caller_id,
            context.identity_source,
            proposed_action.action,
            proposed_action.resource,
            proposed_action.environment,
        )
        outcome = self._rules.get(policy_key)
        if outcome is None:
            return AuthorizationDecision(
                outcome="deny",
                reason="no_matching_rule",
            )

        return AuthorizationDecision(
            outcome=outcome,
            reason=_REASON_BY_OUTCOME[outcome],
        )
