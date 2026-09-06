"""Tests for governed-action execution evidence state-machine integrity."""

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from agentic_lab.application.action_approval import ApprovalStatus, HumanApprovalEvidence
from agentic_lab.application.action_approver_authorization import ApproverAuthorizationDecision
from agentic_lab.application.action_authorization import (
    ActionContext,
    AuthorizationDecision,
    ProposedAction,
)
from agentic_lab.application.action_runtime import ActionExecutionEvidence

ACTION = ProposedAction(
    action="acknowledge_finding",
    resource="finding:demo-001",
    environment="production",
)
OTHER_ACTION = ProposedAction(
    action="acknowledge_finding",
    resource="finding:other",
    environment="production",
)
CONTEXT = ActionContext(caller_id="remediation-agent", identity_source="trusted_composition")
OTHER_CONTEXT = ActionContext(caller_id="other-agent", identity_source="trusted_composition")
APPROVED_AT = datetime(2026, 9, 5, 20, 0, tzinfo=UTC)
EXPIRES_AT = APPROVED_AT + timedelta(minutes=15)

ALLOW = AuthorizationDecision(outcome="allow", reason="explicit_allow")
DENY = AuthorizationDecision(outcome="deny", reason="explicit_deny")
REQUIRE = AuthorizationDecision(
    outcome="require_human_approval",
    reason="human_approval_required",
)
APPROVER_ALLOW = ApproverAuthorizationDecision(outcome="allow", reason="explicit_allow")
APPROVER_DENY = ApproverAuthorizationDecision(outcome="deny", reason="explicit_deny")


def _approval(
    *,
    proposed_action: ProposedAction = ACTION,
    context: ActionContext = CONTEXT,
) -> HumanApprovalEvidence:
    return HumanApprovalEvidence(
        approval_id="approval-001",
        approver_id="soc-reviewer",
        proposed_action=proposed_action,
        context=context,
        approved_at=APPROVED_AT,
        expires_at=EXPIRES_AT,
    )


def _evidence(
    *,
    authorization: AuthorizationDecision,
    approval_status: ApprovalStatus,
    human_approval: HumanApprovalEvidence | None,
    approver_authorization: ApproverAuthorizationDecision | None,
    execution_occurred: bool,
) -> ActionExecutionEvidence:
    return ActionExecutionEvidence(
        proposed_action=ACTION,
        context=CONTEXT,
        authorization=authorization,
        approval_status=approval_status,
        human_approval=human_approval,
        approver_authorization=approver_authorization,
        execution_occurred=execution_occurred,
    )


@pytest.mark.parametrize(
    (
        "authorization",
        "approval_status",
        "human_approval",
        "approver_authorization",
        "execution_occurred",
    ),
    [
        (DENY, "not_applicable", None, None, False),
        (ALLOW, "not_applicable", None, None, True),
        (REQUIRE, "missing", None, None, False),
        (REQUIRE, "invalid", _approval(proposed_action=OTHER_ACTION), None, False),
        (REQUIRE, "invalid", _approval(context=OTHER_CONTEXT), None, False),
        (REQUIRE, "revoked", _approval(), None, False),
        (REQUIRE, "unauthorized_approver", _approval(), APPROVER_DENY, False),
        (REQUIRE, "not_yet_valid", _approval(), APPROVER_ALLOW, False),
        (REQUIRE, "expired", _approval(), APPROVER_ALLOW, False),
        (REQUIRE, "validated", _approval(), APPROVER_ALLOW, True),
    ],
)
def test_all_legal_governed_action_evidence_states_are_accepted(
    authorization: AuthorizationDecision,
    approval_status: ApprovalStatus,
    human_approval: HumanApprovalEvidence | None,
    approver_authorization: ApproverAuthorizationDecision | None,
    execution_occurred: bool,
) -> None:
    """Keep every state the governed runtime can legally emit structurally valid."""
    evidence = _evidence(
        authorization=authorization,
        approval_status=approval_status,
        human_approval=human_approval,
        approver_authorization=approver_authorization,
        execution_occurred=execution_occurred,
    )

    assert evidence.authorization == authorization
    assert evidence.approval_status == approval_status
    assert evidence.execution_occurred is execution_occurred


@pytest.mark.parametrize(
    ("approval_status", "execution_occurred", "message"),
    [
        ("missing", False, "deny authorization requires not_applicable"),
        ("not_applicable", True, "deny authorization cannot record execution"),
    ],
)
def test_deny_evidence_rejects_nonterminal_states(
    approval_status: ApprovalStatus,
    execution_occurred: bool,
    message: str,
) -> None:
    """A caller deny must remain terminal and cannot masquerade as execution."""
    with pytest.raises(ValidationError, match=message):
        _evidence(
            authorization=DENY,
            approval_status=approval_status,
            human_approval=None,
            approver_authorization=None,
            execution_occurred=execution_occurred,
        )


def test_deny_evidence_rejects_human_approval_payload() -> None:
    """Do not attach HITL evidence to a caller-policy deny path."""
    with pytest.raises(ValidationError, match="cannot carry human approval"):
        _evidence(
            authorization=DENY,
            approval_status="not_applicable",
            human_approval=_approval(),
            approver_authorization=None,
            execution_occurred=False,
        )


@pytest.mark.parametrize(
    ("approval_status", "execution_occurred", "message"),
    [
        ("missing", True, "allow authorization requires not_applicable"),
        ("not_applicable", False, "allow authorization requires successful direct execution"),
    ],
)
def test_allow_evidence_rejects_non_direct_execution_states(
    approval_status: ApprovalStatus,
    execution_occurred: bool,
    message: str,
) -> None:
    """A direct caller allow cannot be rewritten as HITL or non-execution evidence."""
    with pytest.raises(ValidationError, match=message):
        _evidence(
            authorization=ALLOW,
            approval_status=approval_status,
            human_approval=None,
            approver_authorization=None,
            execution_occurred=execution_occurred,
        )


def test_allow_evidence_rejects_human_approval_payload() -> None:
    """Keep direct allow evidence independent from unused human authority."""
    with pytest.raises(ValidationError, match="cannot carry human approval"):
        _evidence(
            authorization=ALLOW,
            approval_status="not_applicable",
            human_approval=_approval(),
            approver_authorization=None,
            execution_occurred=True,
        )


def test_approval_required_evidence_rejects_not_applicable_state() -> None:
    """A HITL policy decision must have an observable approval lifecycle outcome."""
    with pytest.raises(ValidationError, match="cannot use not_applicable"):
        _evidence(
            authorization=REQUIRE,
            approval_status="not_applicable",
            human_approval=None,
            approver_authorization=None,
            execution_occurred=False,
        )


@pytest.mark.parametrize(
    ("human_approval", "approver_authorization", "execution_occurred", "message"),
    [
        (_approval(), None, False, "missing approval status cannot carry approval evidence"),
        (None, APPROVER_DENY, False, "missing approval status cannot carry approval evidence"),
        (None, None, True, "missing approval status cannot record execution"),
    ],
)
def test_missing_approval_evidence_rejects_attached_authority_or_execution(
    human_approval: HumanApprovalEvidence | None,
    approver_authorization: ApproverAuthorizationDecision | None,
    execution_occurred: bool,
    message: str,
) -> None:
    """Keep an absent approval capability distinguishable from later HITL states."""
    with pytest.raises(ValidationError, match=message):
        _evidence(
            authorization=REQUIRE,
            approval_status="missing",
            human_approval=human_approval,
            approver_authorization=approver_authorization,
            execution_occurred=execution_occurred,
        )


@pytest.mark.parametrize(
    ("human_approval", "approver_authorization", "execution_occurred", "message"),
    [
        (_approval(), None, False, "invalid approval status requires mismatched approval binding"),
        (
            _approval(proposed_action=OTHER_ACTION),
            APPROVER_DENY,
            False,
            "invalid approval status cannot carry approver authorization",
        ),
        (
            _approval(proposed_action=OTHER_ACTION),
            None,
            True,
            "invalid approval status cannot record execution",
        ),
    ],
)
def test_invalid_approval_state_rejects_fake_or_post_binding_evidence(
    human_approval: HumanApprovalEvidence,
    approver_authorization: ApproverAuthorizationDecision | None,
    execution_occurred: bool,
    message: str,
) -> None:
    """Use invalid only for a claimed approval whose action/context binding actually mismatches."""
    with pytest.raises(ValidationError, match=message):
        _evidence(
            authorization=REQUIRE,
            approval_status="invalid",
            human_approval=human_approval,
            approver_authorization=approver_authorization,
            execution_occurred=execution_occurred,
        )


def test_nonmissing_approval_state_requires_human_evidence() -> None:
    """Do not represent a later approval lifecycle state without the claimed capability."""
    with pytest.raises(ValidationError, match="revoked approval status requires human approval"):
        _evidence(
            authorization=REQUIRE,
            approval_status="revoked",
            human_approval=None,
            approver_authorization=None,
            execution_occurred=False,
        )


@pytest.mark.parametrize(
    ("human_approval", "approver_authorization", "execution_occurred", "message"),
    [
        (
            _approval(proposed_action=OTHER_ACTION),
            None,
            False,
            "revoked approval status requires exact-bound",
        ),
        (_approval(), APPROVER_DENY, False, "revoked approval status cannot carry approver"),
        (_approval(), None, True, "revoked approval status cannot record execution"),
    ],
)
def test_revoked_approval_state_remains_pre_approver_and_nonexecuting(
    human_approval: HumanApprovalEvidence,
    approver_authorization: ApproverAuthorizationDecision | None,
    execution_occurred: bool,
    message: str,
) -> None:
    """Keep revocation terminal after exact binding but before approver entitlement."""
    with pytest.raises(ValidationError, match=message):
        _evidence(
            authorization=REQUIRE,
            approval_status="revoked",
            human_approval=human_approval,
            approver_authorization=approver_authorization,
            execution_occurred=execution_occurred,
        )


@pytest.mark.parametrize(
    ("human_approval", "approver_authorization", "execution_occurred", "message"),
    [
        (
            _approval(context=OTHER_CONTEXT),
            APPROVER_DENY,
            False,
            "unauthorized_approver approval status requires exact-bound",
        ),
        (_approval(), APPROVER_ALLOW, False, "requires a deny approver decision"),
        (_approval(), APPROVER_DENY, True, "cannot record execution"),
    ],
)
def test_unauthorized_approver_state_rejects_wrong_binding_allow_or_execution(
    human_approval: HumanApprovalEvidence,
    approver_authorization: ApproverAuthorizationDecision,
    execution_occurred: bool,
    message: str,
) -> None:
    """An approver deny is meaningful only for exact-bound authority and never executes."""
    with pytest.raises(ValidationError, match=message):
        _evidence(
            authorization=REQUIRE,
            approval_status="unauthorized_approver",
            human_approval=human_approval,
            approver_authorization=approver_authorization,
            execution_occurred=execution_occurred,
        )


@pytest.mark.parametrize("approval_status", ["not_yet_valid", "expired"])
def test_temporal_failure_requires_exact_bound_approved_authority(
    approval_status: ApprovalStatus,
) -> None:
    """Do not record temporal failure before exact binding and approver allow have passed."""
    with pytest.raises(ValidationError, match="requires exact-bound"):
        _evidence(
            authorization=REQUIRE,
            approval_status=approval_status,
            human_approval=_approval(proposed_action=OTHER_ACTION),
            approver_authorization=APPROVER_ALLOW,
            execution_occurred=False,
        )

    with pytest.raises(ValidationError, match="requires an allow approver decision"):
        _evidence(
            authorization=REQUIRE,
            approval_status=approval_status,
            human_approval=_approval(),
            approver_authorization=APPROVER_DENY,
            execution_occurred=False,
        )

    with pytest.raises(ValidationError, match="cannot record execution"):
        _evidence(
            authorization=REQUIRE,
            approval_status=approval_status,
            human_approval=_approval(),
            approver_authorization=APPROVER_ALLOW,
            execution_occurred=True,
        )


def test_validated_state_requires_exact_bound_approved_authority_and_execution() -> None:
    """Validated is the only HITL state that may record mutable execution."""
    with pytest.raises(ValidationError, match="validated approval status requires exact-bound"):
        _evidence(
            authorization=REQUIRE,
            approval_status="validated",
            human_approval=_approval(context=OTHER_CONTEXT),
            approver_authorization=APPROVER_ALLOW,
            execution_occurred=True,
        )

    with pytest.raises(ValidationError, match="requires an allow approver decision"):
        _evidence(
            authorization=REQUIRE,
            approval_status="validated",
            human_approval=_approval(),
            approver_authorization=APPROVER_DENY,
            execution_occurred=True,
        )

    with pytest.raises(ValidationError, match="requires execution evidence"):
        _evidence(
            authorization=REQUIRE,
            approval_status="validated",
            human_approval=_approval(),
            approver_authorization=APPROVER_ALLOW,
            execution_occurred=False,
        )
