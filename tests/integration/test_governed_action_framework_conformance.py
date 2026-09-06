"""Cross-framework conformance tests for governed mutable action execution."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest

from agentic_lab.adapters.agno.action_workflow import AgnoGovernedActionRuntime
from agentic_lab.adapters.crewai.action_flow import run_governed_action_flow
from agentic_lab.adapters.fixtures.action_approvals import InMemoryActionApprovalProvider
from agentic_lab.adapters.fixtures.finding_actions import (
    ACKNOWLEDGE_FINDING_ACTION,
    InMemoryFindingAcknowledgementExecutor,
)
from agentic_lab.adapters.langgraph.action_graph import run_governed_action_graph
from agentic_lab.adapters.llamaindex.action_workflow import (
    LlamaIndexGovernedActionRuntime,
)
from agentic_lab.application.action_approval import ApprovalStatus, HumanApprovalEvidence
from agentic_lab.application.action_approver_authorization import (
    StaticActionApproverAuthorizationPolicy,
)
from agentic_lab.application.action_authorization import (
    ActionAuthorizationRuleKey,
    ActionContext,
    AuthorizationOutcome,
    AuthorizationReason,
    ProposedAction,
    StaticActionAuthorizationPolicy,
)
from agentic_lab.application.action_runtime import (
    ActionExecutionEvidence,
    GovernedActionRuntime,
)

_FINDING_RESOURCE = "finding:demo-001"
_ALLOWED_CALLER = "remediation-agent"
_APPROVED_AT = datetime(2026, 9, 5, 20, 0, tzinfo=UTC)
_NOW = _APPROVED_AT + timedelta(minutes=5)
_EXPIRES_AT = _APPROVED_AT + timedelta(minutes=15)

_RULES: dict[ActionAuthorizationRuleKey, AuthorizationOutcome] = {
    (
        _ALLOWED_CALLER,
        "trusted_composition",
        ACKNOWLEDGE_FINDING_ACTION,
        _FINDING_RESOURCE,
        "test",
    ): "allow",
    (
        _ALLOWED_CALLER,
        "trusted_composition",
        ACKNOWLEDGE_FINDING_ACTION,
        _FINDING_RESOURCE,
        "staging",
    ): "deny",
    (
        _ALLOWED_CALLER,
        "trusted_composition",
        ACKNOWLEDGE_FINDING_ACTION,
        _FINDING_RESOURCE,
        "production",
    ): "require_human_approval",
}


@dataclass(frozen=True, slots=True)
class _Scenario:
    """Describe one framework-neutral authorization and execution expectation."""

    name: str
    proposed_action: ProposedAction
    context: ActionContext
    with_approval: bool
    expected_outcome: AuthorizationOutcome
    expected_reason: AuthorizationReason
    expected_approval_status: ApprovalStatus
    expected_execution: bool
    approver_id: str = "security-reviewer"
    approval_expires_at: datetime | None = None
    revoke_approval: bool = False


def _action(
    *,
    resource: str = _FINDING_RESOURCE,
    environment: str = "test",
) -> ProposedAction:
    return ProposedAction(
        action=ACKNOWLEDGE_FINDING_ACTION,
        resource=resource,
        environment=environment,
    )


_SCENARIOS: tuple[_Scenario, ...] = (
    _Scenario(
        name="exact-allow",
        proposed_action=_action(),
        context=ActionContext(caller_id=_ALLOWED_CALLER),
        with_approval=False,
        expected_outcome="allow",
        expected_reason="explicit_allow",
        expected_approval_status="not_applicable",
        expected_execution=True,
    ),
    _Scenario(
        name="explicit-deny",
        proposed_action=_action(environment="staging"),
        context=ActionContext(caller_id=_ALLOWED_CALLER),
        with_approval=False,
        expected_outcome="deny",
        expected_reason="explicit_deny",
        expected_approval_status="not_applicable",
        expected_execution=False,
    ),
    _Scenario(
        name="approval-missing",
        proposed_action=_action(environment="production"),
        context=ActionContext(caller_id=_ALLOWED_CALLER),
        with_approval=False,
        expected_outcome="require_human_approval",
        expected_reason="human_approval_required",
        expected_approval_status="missing",
        expected_execution=False,
    ),
    _Scenario(
        name="approval-validated",
        proposed_action=_action(environment="production"),
        context=ActionContext(caller_id=_ALLOWED_CALLER),
        with_approval=True,
        expected_outcome="require_human_approval",
        expected_reason="human_approval_required",
        expected_approval_status="validated",
        expected_execution=True,
    ),
    _Scenario(
        name="approver-unauthorized",
        proposed_action=_action(environment="production"),
        context=ActionContext(caller_id=_ALLOWED_CALLER),
        with_approval=True,
        expected_outcome="require_human_approval",
        expected_reason="human_approval_required",
        expected_approval_status="unauthorized_approver",
        expected_execution=False,
        approver_id="unprivileged-reviewer",
    ),
    _Scenario(
        name="approval-expired",
        proposed_action=_action(environment="production"),
        context=ActionContext(caller_id=_ALLOWED_CALLER),
        with_approval=True,
        expected_outcome="require_human_approval",
        expected_reason="human_approval_required",
        expected_approval_status="expired",
        expected_execution=False,
        approval_expires_at=_NOW,
    ),
    _Scenario(
        name="approval-revoked",
        proposed_action=_action(environment="production"),
        context=ActionContext(caller_id=_ALLOWED_CALLER),
        with_approval=True,
        expected_outcome="require_human_approval",
        expected_reason="human_approval_required",
        expected_approval_status="revoked",
        expected_execution=False,
        revoke_approval=True,
    ),
    _Scenario(
        name="caller-mismatch",
        proposed_action=_action(),
        context=ActionContext(caller_id="unprivileged-agent"),
        with_approval=False,
        expected_outcome="deny",
        expected_reason="no_matching_rule",
        expected_approval_status="not_applicable",
        expected_execution=False,
    ),
    _Scenario(
        name="identity-source-mismatch",
        proposed_action=_action(),
        context=ActionContext(caller_id=_ALLOWED_CALLER, identity_source="api_key"),
        with_approval=False,
        expected_outcome="deny",
        expected_reason="no_matching_rule",
        expected_approval_status="not_applicable",
        expected_execution=False,
    ),
    _Scenario(
        name="resource-escalation",
        proposed_action=_action(resource="finding:demo-999"),
        context=ActionContext(caller_id=_ALLOWED_CALLER),
        with_approval=False,
        expected_outcome="deny",
        expected_reason="no_matching_rule",
        expected_approval_status="not_applicable",
        expected_execution=False,
    ),
)


class FixedApprovalClock:
    """Return deterministic application time for framework conformance."""

    def now(self) -> datetime:
        """Return the fixed current time shared by baseline and adapters."""
        return _NOW


def _runtime(
    executor: InMemoryFindingAcknowledgementExecutor,
    scenario: _Scenario,
) -> GovernedActionRuntime:
    approvals: tuple[HumanApprovalEvidence, ...] = ()
    if scenario.with_approval:
        approvals = (
            HumanApprovalEvidence(
                approval_id="approval-conformance-001",
                approver_id=scenario.approver_id,
                proposed_action=scenario.proposed_action,
                context=scenario.context,
                approved_at=_APPROVED_AT,
                expires_at=scenario.approval_expires_at or _EXPIRES_AT,
            ),
        )

    approval_provider = InMemoryActionApprovalProvider(approvals)
    if scenario.revoke_approval:
        if not approvals:
            raise AssertionError("revocation scenario requires approval evidence")
        if not approval_provider.revoke_approval(approvals[0].approval_id):
            raise AssertionError("expected unclaimed approval revocation to succeed")

    return GovernedActionRuntime(
        authorizer=StaticActionAuthorizationPolicy(_RULES),
        executor=executor,
        approval_provider=approval_provider,
        approval_clock=FixedApprovalClock(),
        approver_authorizer=StaticActionApproverAuthorizationPolicy(
            {
                (
                    "security-reviewer",
                    _ALLOWED_CALLER,
                    "trusted_composition",
                    ACKNOWLEDGE_FINDING_ACTION,
                    _FINDING_RESOURCE,
                    "production",
                ): "allow"
            }
        ),
    )


FrameworkRunner = Callable[
    [GovernedActionRuntime, ActionContext, ProposedAction],
    ActionExecutionEvidence,
]


def _run_langgraph(
    runtime: GovernedActionRuntime,
    context: ActionContext,
    proposed_action: ProposedAction,
) -> ActionExecutionEvidence:
    return run_governed_action_graph(runtime, context, proposed_action)["execution_evidence"]


def _run_crewai(
    runtime: GovernedActionRuntime,
    context: ActionContext,
    proposed_action: ProposedAction,
) -> ActionExecutionEvidence:
    return run_governed_action_flow(runtime, context, proposed_action)


def _run_llamaindex(
    runtime: GovernedActionRuntime,
    context: ActionContext,
    proposed_action: ProposedAction,
) -> ActionExecutionEvidence:
    return LlamaIndexGovernedActionRuntime(runtime, context).run(proposed_action)


def _run_agno(
    runtime: GovernedActionRuntime,
    context: ActionContext,
    proposed_action: ProposedAction,
) -> ActionExecutionEvidence:
    return AgnoGovernedActionRuntime(runtime, context).run(proposed_action)


_FRAMEWORK_RUNNERS: tuple[tuple[str, FrameworkRunner], ...] = (
    ("langgraph", _run_langgraph),
    ("crewai", _run_crewai),
    ("llamaindex", _run_llamaindex),
    ("agno", _run_agno),
)


def _assert_expected_behavior(
    evidence: ActionExecutionEvidence,
    executor: InMemoryFindingAcknowledgementExecutor,
    scenario: _Scenario,
) -> None:
    assert evidence.authorization.outcome == scenario.expected_outcome
    assert evidence.authorization.reason == scenario.expected_reason
    assert evidence.approval_status == scenario.expected_approval_status
    assert evidence.execution_occurred is scenario.expected_execution
    assert executor.execution_count == int(scenario.expected_execution)
    assert executor.is_acknowledged(_FINDING_RESOURCE) is scenario.expected_execution


@pytest.mark.parametrize(
    ("framework_name", "runner"),
    _FRAMEWORK_RUNNERS,
    ids=[name for name, _ in _FRAMEWORK_RUNNERS],
)
def test_framework_governed_actions_match_application_baseline(
    framework_name: str,
    runner: FrameworkRunner,
) -> None:
    """Require every framework to preserve application authority and side effects."""
    for scenario in _SCENARIOS:
        baseline_executor = InMemoryFindingAcknowledgementExecutor([_FINDING_RESOURCE])
        baseline_evidence = _runtime(baseline_executor, scenario).execute(
            scenario.proposed_action,
            scenario.context,
        )
        _assert_expected_behavior(baseline_evidence, baseline_executor, scenario)

        framework_executor = InMemoryFindingAcknowledgementExecutor([_FINDING_RESOURCE])
        framework_evidence = runner(
            _runtime(framework_executor, scenario),
            scenario.context,
            scenario.proposed_action,
        )
        _assert_expected_behavior(framework_evidence, framework_executor, scenario)

        assert framework_evidence == baseline_evidence, (
            f"{framework_name} diverged from the application baseline for {scenario.name}"
        )
