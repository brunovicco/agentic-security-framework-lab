"""Concurrency regressions for process-local governed human approval execution."""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier

from agentic_lab.adapters.fixtures.action_approvals import InMemoryActionApprovalProvider
from agentic_lab.adapters.fixtures.finding_actions import (
    InMemoryFindingAcknowledgementExecutor,
)
from agentic_lab.application.action_approval import HumanApprovalEvidence
from agentic_lab.application.action_approver_authorization import (
    StaticActionApproverAuthorizationPolicy,
)
from agentic_lab.application.action_authorization import (
    ActionAuthorizationRuleKey,
    ActionContext,
    AuthorizationOutcome,
    ProposedAction,
    StaticActionAuthorizationPolicy,
)
from agentic_lab.application.action_runtime import (
    ActionExecutionEvidence,
    GovernedActionRuntime,
)

FINDING_RESOURCE = "finding:demo-001"
APPROVED_AT = datetime(2026, 9, 5, 20, 0, tzinfo=UTC)
EXPIRES_AT = APPROVED_AT + timedelta(minutes=15)
VALID_NOW = APPROVED_AT + timedelta(minutes=5)


class FixedApprovalClock:
    """Return deterministic trusted time for concurrent approval checks."""

    def now(self) -> datetime:
        """Return one timezone-aware instant inside the approval validity window."""
        return VALID_NOW


def test_concurrent_runtime_attempts_consume_one_approval_once() -> None:
    """Permit at most one mutable runtime execution for one approval capability."""
    proposed_action = ProposedAction(
        action="acknowledge_finding",
        resource=FINDING_RESOURCE,
        environment="production",
    )
    context = ActionContext(
        caller_id="remediation-agent",
        identity_source="trusted_composition",
    )
    rule_key: ActionAuthorizationRuleKey = (
        context.caller_id,
        context.identity_source,
        proposed_action.action,
        proposed_action.resource,
        proposed_action.environment,
    )
    rules: dict[ActionAuthorizationRuleKey, AuthorizationOutcome] = {
        rule_key: "require_human_approval"
    }
    approval = HumanApprovalEvidence(
        approval_id="approval-concurrent-001",
        approver_id="soc-reviewer",
        proposed_action=proposed_action,
        context=context,
        approved_at=APPROVED_AT,
        expires_at=EXPIRES_AT,
    )
    executor = InMemoryFindingAcknowledgementExecutor([FINDING_RESOURCE])
    runtime = GovernedActionRuntime(
        authorizer=StaticActionAuthorizationPolicy(rules),
        executor=executor,
        approval_provider=InMemoryActionApprovalProvider([approval]),
        approval_clock=FixedApprovalClock(),
        approver_authorizer=StaticActionApproverAuthorizationPolicy(
            {
                (
                    "soc-reviewer",
                    context.caller_id,
                    context.identity_source,
                    proposed_action.action,
                    proposed_action.resource,
                    proposed_action.environment,
                ): "allow"
            }
        ),
    )
    participants = 8
    barrier = Barrier(participants)

    def execute() -> ActionExecutionEvidence:
        barrier.wait()
        return runtime.execute(proposed_action, context)

    with ThreadPoolExecutor(max_workers=participants) as pool:
        futures = [pool.submit(execute) for _ in range(participants)]
        evidence = [future.result() for future in futures]

    statuses = [item.approval_status for item in evidence]
    assert statuses.count("validated") == 1
    assert statuses.count("missing") == participants - 1
    validated = next(item for item in evidence if item.approval_status == "validated")
    assert validated.approver_authorization is not None
    assert validated.approver_authorization.outcome == "allow"
    assert sum(item.execution_occurred for item in evidence) == 1
    assert executor.execution_count == 1
    assert executor.is_acknowledged(FINDING_RESOURCE) is True
