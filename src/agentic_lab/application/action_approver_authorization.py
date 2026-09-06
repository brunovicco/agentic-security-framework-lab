"""Deterministic authorization for human approvers of governed actions."""

from collections.abc import Mapping
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict

from agentic_lab.application.action_authorization import (
    ActionContext,
    CallerIdentitySource,
    ProposedAction,
)

ApproverAuthorizationOutcome = Literal["allow", "deny"]
ApproverAuthorizationReason = Literal[
    "explicit_allow",
    "explicit_deny",
    "no_matching_rule",
]
ApproverAuthorizationRuleKey = tuple[
    str,
    str,
    CallerIdentitySource,
    str,
    str,
    str,
]

_REASON_BY_OUTCOME: dict[ApproverAuthorizationOutcome, ApproverAuthorizationReason] = {
    "allow": "explicit_allow",
    "deny": "explicit_deny",
}


class ApproverAuthorizationDecision(BaseModel):
    """Record whether one trusted approver is entitled for an exact action scope."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    outcome: ApproverAuthorizationOutcome
    reason: ApproverAuthorizationReason


class ActionApproverAuthorizer(Protocol):
    """Decide whether one trusted approver may approve an exact governed action."""

    def authorize(
        self,
        approver_id: str,
        proposed_action: ProposedAction,
        context: ActionContext,
    ) -> ApproverAuthorizationDecision:
        """Return one deterministic approver entitlement decision."""
        ...


class StaticActionApproverAuthorizationPolicy:
    """Authorize exact approver/caller/source/action/resource/environment scopes."""

    def __init__(
        self,
        rules: Mapping[ApproverAuthorizationRuleKey, ApproverAuthorizationOutcome],
    ) -> None:
        """Copy trusted approver rules so later caller mutation cannot change policy."""
        self._rules = dict(rules)

    def authorize(
        self,
        approver_id: str,
        proposed_action: ProposedAction,
        context: ActionContext,
    ) -> ApproverAuthorizationDecision:
        """Apply one exact approver rule or deny fail-closed when no rule exists."""
        policy_key: ApproverAuthorizationRuleKey = (
            approver_id,
            context.caller_id,
            context.identity_source,
            proposed_action.action,
            proposed_action.resource,
            proposed_action.environment,
        )
        outcome = self._rules.get(policy_key)
        if outcome is None:
            return ApproverAuthorizationDecision(
                outcome="deny",
                reason="no_matching_rule",
            )

        return ApproverAuthorizationDecision(
            outcome=outcome,
            reason=_REASON_BY_OUTCOME[outcome],
        )


class NoActionApproverAuthorizer:
    """Fail closed when no trusted approver-authorization policy is configured."""

    def authorize(
        self,
        approver_id: str,
        proposed_action: ProposedAction,
        context: ActionContext,
    ) -> ApproverAuthorizationDecision:
        """Deny unknown approver authority without inferring entitlement from evidence."""
        del approver_id, proposed_action, context
        return ApproverAuthorizationDecision(
            outcome="deny",
            reason="no_matching_rule",
        )


NULL_ACTION_APPROVER_AUTHORIZER: ActionApproverAuthorizer = NoActionApproverAuthorizer()
