"""LangGraph adapter for framework-neutral governed action execution."""

# LangGraph's public typing surface contains partial/unknown types under Pyright
# strict mode. Keep those diagnostics isolated at this framework boundary.
# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false

from typing import Protocol, TypedDict, cast

from langgraph.graph import END, START, StateGraph

from agentic_lab.application.action_authorization import ProposedAction
from agentic_lab.application.action_runtime import (
    ActionExecutionEvidence,
    GovernedActionRuntime,
)


class GovernedActionGraphInput(TypedDict):
    """Public input accepted by the governed LangGraph action workflow."""

    proposed_action: ProposedAction


class GovernedActionGraphOutput(TypedDict):
    """Public output returned by the governed LangGraph action workflow."""

    execution_evidence: ActionExecutionEvidence


class _GovernedActionGraphState(TypedDict, total=False):
    """Internal state for framework-owned orchestration only."""

    proposed_action: ProposedAction
    execution_evidence: ActionExecutionEvidence


class _InvokableActionGraph(Protocol):
    """Minimal local boundary for the compiled LangGraph action workflow."""

    def invoke(self, input: GovernedActionGraphInput) -> GovernedActionGraphOutput:
        """Run the governed action graph."""
        ...


def execute_governed_action(
    state: _GovernedActionGraphState,
    runtime: GovernedActionRuntime,
) -> _GovernedActionGraphState:
    """Delegate authorization and enforcement to the application runtime."""
    proposed_action = state.get("proposed_action")
    if proposed_action is None:
        raise RuntimeError("Governed action execution requires a proposed action")

    return {
        "execution_evidence": runtime.execute(proposed_action),
    }


def build_governed_action_graph(
    runtime: GovernedActionRuntime,
) -> _InvokableActionGraph:
    """Build a LangGraph workflow that consumes the governed runtime boundary."""

    def runtime_node(
        state: _GovernedActionGraphState,
    ) -> _GovernedActionGraphState:
        return execute_governed_action(state, runtime)

    builder = StateGraph(
        _GovernedActionGraphState,
        input_schema=GovernedActionGraphInput,
        output_schema=GovernedActionGraphOutput,
    )
    builder.add_node("execute_governed_action", runtime_node)
    builder.add_edge(START, "execute_governed_action")
    builder.add_edge("execute_governed_action", END)

    return cast(_InvokableActionGraph, builder.compile())


def run_governed_action_graph(
    runtime: GovernedActionRuntime,
    proposed_action: ProposedAction,
) -> GovernedActionGraphOutput:
    """Run one proposed action through LangGraph and the governed runtime."""
    graph = build_governed_action_graph(runtime)
    graph_input: GovernedActionGraphInput = {
        "proposed_action": proposed_action,
    }
    return graph.invoke(graph_input)
