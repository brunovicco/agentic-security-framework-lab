"""LangGraph regression proving trusted approval stays runtime-owned."""

from agentic_lab.adapters.fixtures.action_approvals import InMemoryActionApprovalProvider
from agentic_lab.adapters.fixtures.finding_actions import (
    InMemoryFindingAcknowledgementExecutor,
)
from agentic_lab.adapters.langgraph.action_graph import run_governed_action_graph
from agentic_lab.application.action_approval import HumanApprovalEvidence
from agentic_lab.application.action_authorization import (
    ActionAuthorizationRuleKey,
    ActionContext,
    AuthorizationOutcome,
    ProposedAction,
    StaticActionAuthorizationPolicy,
)
from agentic_lab.application.action_runtime import GovernedActionRuntime

FINDING_RESOURCE = "finding:demo-001"
REMEDIATION_AGENT = "remediation-agent"


def test_langgraph_executes_validated_approval_without_hitl_logic_in_graph() -> None:
    """Consume runtime HITL enforcement without redefining approval in LangGraph."""
    proposed_action = ProposedAction(
        action="acknowledge_finding",
        resource=FINDING_RESOURCE,
        environment="production",
    )
    context = ActionContext(caller_id=REMEDIATION_AGENT)
    approval = HumanApprovalEvidence(
        approval_id="approval-001",
        approver_id="soc-reviewer",
        proposed_action=proposed_action,
        context=context,
    )
    rules: dict[ActionAuthorizationRuleKey, AuthorizationOutcome] = {
        (
            REMEDIATION_AGENT,
            "trusted_composition",
            "acknowledge_finding",
            FINDING_RESOURCE,
            "production",
        ): "require_human_approval",
    }
    executor = InMemoryFindingAcknowledgementExecutor([FINDING_RESOURCE])
    runtime = GovernedActionRuntime(
        authorizer=StaticActionAuthorizationPolicy(rules),
        executor=executor,
        approval_provider=InMemoryActionApprovalProvider([approval]),
    )

    output = run_governed_action_graph(runtime, context, proposed_action)

    evidence = output["execution_evidence"]
    assert evidence.authorization.outcome == "require_human_approval"
    assert evidence.approval_status == "validated"
    assert evidence.human_approval == approval
    assert evidence.execution_occurred is True
    assert executor.is_acknowledged(FINDING_RESOURCE) is True
    assert executor.execution_count == 1
