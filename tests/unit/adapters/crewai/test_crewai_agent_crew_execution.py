"""Tests for the CrewAI Agent/Crew logical execution boundary."""

from collections.abc import Sequence

import pytest

from agentic_lab.adapters.crewai.analyzer import CrewAIUsage
from agentic_lab.adapters.crewai.execution import CrewAIAgentCrewRuntime
from agentic_lab.adapters.fixtures.evaluation import load_evaluation_scenarios
from agentic_lab.application.contracts import AssetAssessment, LLMAnalysisDraft
from agentic_lab.application.evidence import AnalysisEvidenceBundle
from agentic_lab.observability import AnalysisExecutionObservation


class RecordingObserver:
    """Collect completed logical observations without a telemetry backend."""

    def __init__(self) -> None:
        self.observations: list[AnalysisExecutionObservation] = []

    def record(self, observation: AnalysisExecutionObservation) -> None:
        self.observations.append(observation)


class StubUsageAwareRunner:
    """Return controlled drafts and normalized usage for one logical execution."""

    def __init__(
        self,
        drafts: Sequence[LLMAnalysisDraft],
        *,
        final_usage: CrewAIUsage,
        stale_usage: CrewAIUsage | None = None,
        fail_on_run: bool = False,
    ) -> None:
        self._drafts = iter(drafts)
        self._final_usage = final_usage
        self._stale_usage = stale_usage if stale_usage is not None else CrewAIUsage()
        self._consume_count = 0
        self._fail_on_run = fail_on_run
        self.run_calls = 0

    @property
    def consume_count(self) -> int:
        """Expose usage-consumption count for boundary assertions."""
        return self._consume_count

    def run(self, task_description: str) -> LLMAnalysisDraft:
        del task_description
        self.run_calls += 1
        if self._fail_on_run:
            raise RuntimeError("controlled CrewAI Agent/Crew failure")
        return next(self._drafts)

    def consume_usage(self) -> CrewAIUsage:
        self._consume_count += 1
        if self._consume_count == 1:
            return self._stale_usage
        if self._consume_count == 2:
            return self._final_usage
        return CrewAIUsage()


def _evidence_bundle() -> AnalysisEvidenceBundle:
    scenario = load_evaluation_scenarios()[0]
    return {
        "vulnerability": scenario.vulnerability,
        "assets": scenario.assets,
        "policy": scenario.policy,
    }


def _correct_draft() -> LLMAnalysisDraft:
    return LLMAnalysisDraft(
        assets=(
            AssetAssessment(
                asset_id="api-prod-01",
                status="affected",
                rationale="4.1 is below the exclusive affected boundary.",
            ),
            AssetAssessment(
                asset_id="api-prod-02",
                status="not_affected",
                rationale="4.4 is outside the affected range.",
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
                rationale="4.4 is not affected.",
            ),
        ),
        recommendation="No remediation required.",
        confidence=0.9,
    )


def test_agent_crew_runtime_emits_one_first_pass_observation() -> None:
    runner = StubUsageAwareRunner(
        [_correct_draft()],
        final_usage=CrewAIUsage(
            input_tokens=100,
            output_tokens=20,
            total_tokens=120,
            model_calls=1,
        ),
    )
    observer = RecordingObserver()

    execution = CrewAIAgentCrewRuntime(runner=runner, observer=observer).run(
        _evidence_bundle()
    )

    assert execution.output.analysis_attempts == 1
    assert execution.usage.model_calls == 1
    assert observer.observations == [
        AnalysisExecutionObservation(
            framework="crewai",
            workflow="crewai-agent-crew",
            analysis_source="llm",
            validation_passed=True,
            analysis_attempts=1,
            model_calls=1,
            requires_human_review=True,
        )
    ]


def test_agent_crew_runtime_preserves_framework_calls_across_retry() -> None:
    runner = StubUsageAwareRunner(
        [_wrong_draft(), _correct_draft()],
        final_usage=CrewAIUsage(
            input_tokens=230,
            output_tokens=55,
            total_tokens=285,
            model_calls=3,
        ),
    )
    observer = RecordingObserver()

    execution = CrewAIAgentCrewRuntime(runner=runner, observer=observer).run(
        _evidence_bundle()
    )

    assert execution.output.analysis_attempts == 2
    assert execution.output.analysis_source == "llm"
    assert runner.run_calls == 2
    assert execution.usage.model_calls == 3
    assert observer.observations[0].analysis_attempts == 2
    assert observer.observations[0].model_calls == 3


def test_agent_crew_runtime_emits_final_fallback_observation() -> None:
    runner = StubUsageAwareRunner(
        [_wrong_draft(), _wrong_draft()],
        final_usage=CrewAIUsage(
            input_tokens=220,
            output_tokens=50,
            total_tokens=270,
            model_calls=2,
        ),
    )
    observer = RecordingObserver()

    execution = CrewAIAgentCrewRuntime(runner=runner, observer=observer).run(
        _evidence_bundle()
    )

    assert execution.output.analysis_source == "oracle_fallback"
    assert execution.output.validation_passed is False
    assert len(observer.observations) == 1
    observation = observer.observations[0]
    assert observation.analysis_source == "oracle_fallback"
    assert observation.validation_passed is False
    assert observation.analysis_attempts == 2
    assert observation.model_calls == 2


def test_agent_crew_runtime_rejects_stale_usage_before_execution() -> None:
    runner = StubUsageAwareRunner(
        [_correct_draft()],
        stale_usage=CrewAIUsage(
            input_tokens=10,
            output_tokens=2,
            total_tokens=12,
            model_calls=1,
        ),
        final_usage=CrewAIUsage(),
    )
    observer = RecordingObserver()

    with pytest.raises(RuntimeError, match="was not clean before logical execution"):
        CrewAIAgentCrewRuntime(runner=runner, observer=observer).run(_evidence_bundle())

    assert runner.run_calls == 0
    assert observer.observations == []


def test_agent_crew_runtime_rejects_incomplete_model_call_usage() -> None:
    runner = StubUsageAwareRunner(
        [_wrong_draft(), _correct_draft()],
        final_usage=CrewAIUsage(
            input_tokens=200,
            output_tokens=40,
            total_tokens=240,
            model_calls=1,
        ),
    )
    observer = RecordingObserver()

    with pytest.raises(RuntimeError, match="fewer model calls than analysis attempts"):
        CrewAIAgentCrewRuntime(runner=runner, observer=observer).run(_evidence_bundle())

    assert observer.observations == []


def test_agent_crew_runtime_drains_failed_usage_without_observation() -> None:
    runner = StubUsageAwareRunner(
        [],
        final_usage=CrewAIUsage(
            input_tokens=40,
            output_tokens=5,
            total_tokens=45,
            model_calls=1,
        ),
        fail_on_run=True,
    )
    observer = RecordingObserver()

    with pytest.raises(RuntimeError, match="controlled CrewAI Agent/Crew failure"):
        CrewAIAgentCrewRuntime(runner=runner, observer=observer).run(_evidence_bundle())

    assert runner.consume_count == 2
    assert observer.observations == []
