"""Tests for CrewAI Flow logical execution observations."""

from dataclasses import dataclass

import pytest
from pytest import MonkeyPatch

from agentic_lab.adapters.crewai import flow as crewai_flow_module
from agentic_lab.adapters.crewai.flow import (
    CrewAIFlowRuntime,
    CrewAIValidatedFlowState,
)
from agentic_lab.adapters.fixtures.evaluation import load_evaluation_scenarios
from agentic_lab.application.evidence import AnalysisEvidenceBundle
from agentic_lab.application.oracle import assess_assets_deterministically
from agentic_lab.application.validated_analysis import AnalysisSource, build_analysis_result
from agentic_lab.observability import AnalysisExecutionObservation


class RecordingObserver:
    """Collect completed logical observations without an external backend."""

    def __init__(self) -> None:
        self.observations: list[AnalysisExecutionObservation] = []

    def record(self, observation: AnalysisExecutionObservation) -> None:
        self.observations.append(observation)


@dataclass(frozen=True, slots=True)
class StubUsageMetrics:
    """Expose the framework usage fields consumed by CrewAIFlowRuntime."""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    successful_requests: int


class StubRuntimeFlow:
    """Provide controlled final Flow state and framework-reported usage."""

    def __init__(
        self,
        state: CrewAIValidatedFlowState,
        *,
        analysis_source: AnalysisSource,
        validation_passed: bool,
        analysis_attempts: int,
        model_calls: int,
        fail_kickoff: bool = False,
    ) -> None:
        scenario = load_evaluation_scenarios()[0]
        assessments = assess_assets_deterministically(
            vulnerability=scenario.vulnerability,
            assets=scenario.assets,
        )
        state.analysis_source = analysis_source
        state.validation_passed = validation_passed
        state.validation_reason = "controlled test validation"
        state.analysis_attempts = analysis_attempts
        state.result = build_analysis_result(
            vulnerability=scenario.vulnerability,
            assessments=assessments,
            recommendation="Controlled observability test result.",
            confidence=1.0,
            requires_human_review=True,
        )
        self.state = state
        self.usage_metrics = StubUsageMetrics(
            prompt_tokens=100,
            completion_tokens=20,
            total_tokens=120,
            successful_requests=model_calls,
        )
        self._fail_kickoff = fail_kickoff

    def kickoff(self) -> None:
        if self._fail_kickoff:
            raise RuntimeError("controlled CrewAI Flow failure")


def _evidence_bundle() -> AnalysisEvidenceBundle:
    scenario = load_evaluation_scenarios()[0]
    return {
        "vulnerability": scenario.vulnerability,
        "assets": scenario.assets,
        "policy": scenario.policy,
    }


def _install_flow(
    monkeypatch: MonkeyPatch,
    *,
    analysis_source: AnalysisSource = "llm",
    validation_passed: bool = True,
    analysis_attempts: int = 1,
    model_calls: int = 1,
    fail_kickoff: bool = False,
) -> None:
    def factory(
        *,
        initial_state: CrewAIValidatedFlowState,
        tracing: bool | None = None,
    ) -> StubRuntimeFlow:
        assert tracing is False
        return StubRuntimeFlow(
            initial_state,
            analysis_source=analysis_source,
            validation_passed=validation_passed,
            analysis_attempts=analysis_attempts,
            model_calls=model_calls,
            fail_kickoff=fail_kickoff,
        )

    monkeypatch.setattr(crewai_flow_module, "CrewAIValidatedAnalysisFlow", factory)


def test_flow_runtime_emits_one_first_pass_observation(monkeypatch: MonkeyPatch) -> None:
    _install_flow(monkeypatch)
    observer = RecordingObserver()
    runtime = CrewAIFlowRuntime(observer=observer)

    execution = runtime.run(_evidence_bundle())

    assert execution.usage.model_calls == 1
    assert observer.observations == [
        AnalysisExecutionObservation(
            framework="crewai",
            workflow="crewai-flow",
            analysis_source="llm",
            validation_passed=True,
            analysis_attempts=1,
            model_calls=1,
            requires_human_review=True,
        )
    ]


def test_flow_runtime_preserves_framework_reported_calls_on_retry(
    monkeypatch: MonkeyPatch,
) -> None:
    _install_flow(monkeypatch, analysis_attempts=2, model_calls=3)
    observer = RecordingObserver()

    execution = CrewAIFlowRuntime(observer=observer).run(_evidence_bundle())

    assert execution.output.analysis_attempts == 2
    assert execution.usage.model_calls == 3
    assert observer.observations[0].analysis_attempts == 2
    assert observer.observations[0].model_calls == 3


def test_flow_runtime_emits_final_fallback_observation(monkeypatch: MonkeyPatch) -> None:
    _install_flow(
        monkeypatch,
        analysis_source="oracle_fallback",
        validation_passed=False,
        analysis_attempts=2,
        model_calls=2,
    )
    observer = RecordingObserver()

    CrewAIFlowRuntime(observer=observer).run(_evidence_bundle())

    assert len(observer.observations) == 1
    observation = observer.observations[0]
    assert observation.analysis_source == "oracle_fallback"
    assert observation.validation_passed is False
    assert observation.analysis_attempts == 2
    assert observation.model_calls == 2


def test_flow_runtime_emits_no_completed_observation_when_kickoff_fails(
    monkeypatch: MonkeyPatch,
) -> None:
    _install_flow(monkeypatch, fail_kickoff=True)
    observer = RecordingObserver()

    with pytest.raises(RuntimeError, match="controlled CrewAI Flow failure"):
        CrewAIFlowRuntime(observer=observer).run(_evidence_bundle())

    assert observer.observations == []
