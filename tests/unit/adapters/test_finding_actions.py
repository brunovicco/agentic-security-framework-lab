"""Tests for the deterministic in-memory finding action adapter."""

import pytest

from agentic_lab.adapters.fixtures.finding_actions import (
    InMemoryFindingAcknowledgementExecutor,
)
from agentic_lab.application.action_authorization import ProposedAction

FINDING_RESOURCE = "finding:demo-001"


def _action(action: str, resource: str = FINDING_RESOURCE) -> ProposedAction:
    return ProposedAction(action=action, resource=resource, environment="test")


def test_acknowledges_known_finding() -> None:
    """Apply the adapter's one supported local mutation deterministically."""
    executor = InMemoryFindingAcknowledgementExecutor([FINDING_RESOURCE])

    executor.execute(_action("acknowledge_finding"))

    assert executor.is_acknowledged(FINDING_RESOURCE) is True
    assert executor.execution_count == 1


def test_rejects_mismatched_action_without_mutation() -> None:
    """Fail on wiring misuse rather than silently applying a different operation."""
    executor = InMemoryFindingAcknowledgementExecutor([FINDING_RESOURCE])

    with pytest.raises(ValueError, match="unsupported action"):
        executor.execute(_action("delete_finding"))

    assert executor.is_acknowledged(FINDING_RESOURCE) is False
    assert executor.execution_count == 0


def test_rejects_unknown_finding_without_mutation() -> None:
    """Fail deterministically when the authorized target does not exist locally."""
    executor = InMemoryFindingAcknowledgementExecutor([FINDING_RESOURCE])

    with pytest.raises(LookupError, match="finding does not exist"):
        executor.execute(_action("acknowledge_finding", resource="finding:missing"))

    assert executor.is_acknowledged(FINDING_RESOURCE) is False
    assert executor.execution_count == 0
