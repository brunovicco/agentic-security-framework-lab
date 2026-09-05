"""Tests for the observed Agno Workflow execution boundary."""

from collections.abc import Sequence

import pytest

from agentic_lab.adapters.agno.analyzer import AgnoUsage
from agentic_lab.adapters.agno.execution import AgnoObservedWorkflowRuntime
from agentic_lab.adapters.agno.workflow import AgnoWorkflowRuntime
from agentic_lab.adapters.fixtures.demo import (
    DEMO_CVE_ID,
    load_asset_inventory,
    load_security_policy,
    load_vulnerability_evidence,
)
from agentic_lab.application.contracts import AssetAssessment, LLMAnalysisDraft
from agentic_lab.application.evidence import AnalysisEvidenceBundle
from agentic_lab.observability import AnalysisExecutionObservation


class RecordingObserver:
    """Collect completed observations without an external telemetry backend."""

    def __init__(self) -> None:
        self.observations: list[AnalysisExecutionObservation] = []

    def record(self, observation: AnalysisExecutionObservation) -> None:
        self.observations.append(observation)


class StubUsageRunner:
    """Return controlled drafts and isolated usage without provider calls."""

    def __init__(
        self,
        drafts: Sequence[LLMAnalysisDraft],
        *,
        model_calls: int | None = None,
        fail_on_run: bool = False,
    ) -> None:
        self._drafts = tuple(drafts)
        self._model_calls = model_calls
        self._fail_on_run = fail_on_run
        self.calls: list[tuple[str, str]] = []

    def run(self, system_prompt: str, user_prompt: str) -> LLMAnalysisDraft:
        if self._fail_on_run:
            raise RuntimeError("controlled Agno Workflow failure")
        self.calls.append((system_prompt, user_prompt))
        return self._drafts[len(self.calls) - 1]

    def consume_usage(self) -> AgnoUsage:
        model_calls = self._model_calls if self._model_calls is not None else len(self.calls)
        return AgnoUsage(
            input_tokens=500 * max(model_calls, 0),
            output_tokens=100 * max(model_calls, 0),
            total_tokens=600 * max(model_calls, 0),
            model_calls=model_calls,
        )


def _evidence_bundle() -> AnalysisEvidenceBundle:
    return {
        "vulnerability": load_vulnerability_evidence(DEMO_CVE_ID),
        "assets": load_asset_inventory(),
        "policy": load_security_policy(),
    }


def _correct_draft() -> LLMAnalysisDraft:
    return LLMAnalysisDraft(
        assets=(
            AssetAssessment(
                asset_id="api-prod-01",
                status="affected",
                rationale="Version 4.1 is below the exclusive fixed boundary.",
            ),
            AssetAssessment(
                asset_id="api-prod-02",
                status="not_affected",
                rationale="Version 4.4 is outside the affected range.",
            ),
        ),
        recommendation="Upgrade the affected production asset.",
        confidence=0.98,
    )


def _wrong_draft() -> LLMAnalysisDraft:
    return LLMAnalysisDraft(
        assets=(
            AssetAssessment(
                asset_id="api-prod-01",
                status="not_affected",
                rationale="Incorrect controlled test conclusion.",
            ),
            AssetAssessment(
                asset_id="api-prod-02",
                status="not_affected",
                rationale="Version 4.4 is not affected.",
            ),
        ),
        recommendation="No remediation required.",
        confidence=0.9,
    )


def _runtime(
    runner: StubUsageRunner,
    observer: RecordingObserver,
) -> AgnoObservedWorkflowRuntime:
    def runner_factory() -> StubUsageRunner:
        return runner

    return AgnoObservedWorkflowRuntime(
        runtime=AgnoWorkflowRuntime(runner_factory=runner_factory),
        observer=observer,
    )


def test_observed_runtime_emits_one_first_pass_observation() -> None:
    runner = StubUsageRunner([_correct_draft()])
    observer = RecordingObserver()

    execution = _runtime(runner, observer).run(_evidence_bundle())

    assert execution.output.analysis_attempts == 1
    assert observer.observations == [
        AnalysisExecutionObservation(
            framework="agno",
            workflow="agno-workflow",
            analysis_source="llm",
            validation_passed=True,
            analysis_attempts=1,
            model_calls=1,
            requires_human_review=True,
        )
    ]


def test_observed_runtime_preserves_independent_model_calls_across_retry() -> None:
    runner = StubUsageRunner(
        [_wrong_draft(), _correct_draft()],
        model_calls=3,
    )
    observer = RecordingObserver()

    execution = _runtime(runner, observer).run(_evidence_bundle())

    assert execution.output.analysis_attempts == 2
    assert execution.usage.model_calls == 3
    assert observer.observations[0].analysis_attempts == 2
    assert observer.observations[0].model_calls == 3


def test_observed_runtime_emits_final_fallback_observation() -> None:
    runner = StubUsageRunner([_wrong_draft(), _wrong_draft()])
    observer = RecordingObserver()

    execution = _runtime(runner, observer).run(_evidence_bundle())

    assert execution.output.analysis_source == "oracle_fallback"
    assert execution.output.validation_passed is False
    assert observer.observations[0].analysis_source == "oracle_fallback"
    assert observer.observations[0].validation_passed is False
    assert observer.observations[0].analysis_attempts == 2
    assert observer.observations[0].model_calls == 2


def test_observed_runtime_rejects_incomplete_usage_without_observation() -> None:
    runner = StubUsageRunner(
        [_wrong_draft(), _correct_draft()],
        model_calls=1,
    )
    observer = RecordingObserver()

    with pytest.raises(RuntimeError, match="fewer model calls than analysis attempts"):
        _runtime(runner, observer).run(_evidence_bundle())

    assert observer.observations == []


def test_observed_runtime_emits_no_observation_when_workflow_fails() -> None:
    runner = StubUsageRunner([], fail_on_run=True)
    observer = RecordingObserver()

    with pytest.raises(RuntimeError, match="controlled Agno Workflow failure"):
        _runtime(runner, observer).run(_evidence_bundle())

    assert observer.observations == []
