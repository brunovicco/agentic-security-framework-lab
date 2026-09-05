"""Deterministic local action adapter for governed execution experiments."""

from collections.abc import Iterable

from agentic_lab.application.action_authorization import ProposedAction

ACKNOWLEDGE_FINDING_ACTION = "acknowledge_finding"


class InMemoryFindingAcknowledgementExecutor:
    """Acknowledge known synthetic findings without any external side effect."""

    def __init__(self, findings: Iterable[str]) -> None:
        """Initialize a closed set of known findings for the local experiment."""
        self._findings = frozenset(findings)
        self._acknowledged: set[str] = set()
        self._execution_count = 0

    @property
    def execution_count(self) -> int:
        """Return successful mutable executions independently from policy decisions."""
        return self._execution_count

    def is_acknowledged(self, resource: str) -> bool:
        """Report the observable in-memory state of one finding."""
        return resource in self._acknowledged

    def execute(self, proposed_action: ProposedAction) -> None:
        """Apply the exact local operation after the caller has authorized it."""
        if proposed_action.action != ACKNOWLEDGE_FINDING_ACTION:
            raise ValueError(
                "finding acknowledgement executor received an unsupported action"
            )
        if proposed_action.resource not in self._findings:
            raise LookupError("finding does not exist")

        self._acknowledged.add(proposed_action.resource)
        self._execution_count += 1
