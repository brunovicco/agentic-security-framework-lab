"""Tests for LangGraph logical execution observations."""

import pytest

from agentic_lab.adapters.fixtures.demo import DEMO_CVE_ID
from agentic_lab.adapters.langgraph.llm_graph import run_llm_analysis_graph
from agentic_lab.application.contracts import AssetAssessment, LLMAnalysisDraft
from agentic_lab.application.evidence import AssetInventoryItem, VulnerabilityEvidence
from agentic_lab.observability import AnalysisExecutionObservation


class RecordingObserver:
    """Collect completed logical observations without an external backend."""

    def __init__(self) -> None:
        self.observations: list[AnalysisExecutionObservation] = []

    def record(self, observation: AnalysisExecutionObservation) -> None:
        """Store one observation for assertions."""
        self.observations.append(observation)


class SequentialAnalyzer:
    """Return configured drafts and expose one application-level call per attempt."""

    def __init__(self, drafts: tuple[LLMAnalysisDraft, ...]) -> None:
        self._drafts = drafts
        self._index = 0

    def analyze(
        self,
        vulnerability: VulnerabilityEvidence,
        assets: tuple[AssetInventoryItem, ...],
        feedback: str | None = None,
    ) -> LLMAnalysisDraft:
        """Return the next configured draft."""
        del vulnerability, assets, feedback
        draft = self._drafts[self._index]
        self._index += 1
        return draft


class FailingAnalyzer:
    """Fail before the graph can produce a completed logical result."""

    def analyze(
        self,
        vulnerability: VulnerabilityEvidence,
        assets: tuple[AssetInventoryItem, ...],
        feedback: str | None = None,
    ) -> LLMAnalysisDraft:
        """Raise a controlled runtime failure."""
        del vulnerability, assets, feedback
        raise RuntimeError("controlled analyzer failure")


def _correct_draft() -> LLMAnalysisDraft:
    return LLMAnalysisDraft(
        assets=(
            AssetAssessment(
                asset_id="api-prod-01",
                status="affected",
                rationale="ExampleServer 4.1 is below 4.2.",
            ),
            AssetAssessment(
                asset_id="api-prod-02",
                status="not_affected",
                rationale="ExampleServer 4.4 is not below 4.2.",
            ),
        ),
        recommendation="Patch the affected asset.",
        confidence=0.95,
    )


def _incorrect_draft() -> LLMAnalysisDraft:
    return LLMAnalysisDraft(
        assets=(
            AssetAssessment(
                asset_id="api-prod-01",
                status="not_affected",
                rationale="Incorrect test classification.",
            ),
            AssetAssessment(
                asset_id="api-prod-02",
                status="not_affected",
                rationale="ExampleServer 4.4 is outside the affected range.",
            ),
        ),
        recommendation="No remediation required.",
        confidence=0.6,
    )


def test_first_attempt_emits_one_completed_langgraph_observation() -> None:
    observer = RecordingObserver()

    output = run_llm_analysis_graph(
        SequentialAnalyzer((_correct_draft(),)),
        DEMO_CVE_ID,
        observer=observer,
    )

    assert output["analysis_attempts"] == 1
    assert observer.observations == [
        AnalysisExecutionObservation(
            framework="langgraph",
            workflow="langgraph-evaluator-optimizer",
            analysis_source="llm",
            validation_passed=True,
            analysis_attempts=1,
            model_calls=1,
            requires_human_review=True,
        )
    ]


def test_retry_recovery_emits_only_one_final_observation() -> None:
    observer = RecordingObserver()

    output = run_llm_analysis_graph(
        SequentialAnalyzer((_incorrect_draft(), _correct_draft())),
        DEMO_CVE_ID,
        observer=observer,
    )

    assert output["analysis_source"] == "llm"
    assert output["analysis_attempts"] == 2
    assert len(observer.observations) == 1
    observation = observer.observations[0]
    assert observation.analysis_source == "llm"
    assert observation.validation_passed is True
    assert observation.analysis_attempts == 2
    assert observation.model_calls == 2


def test_fallback_emits_only_one_final_fallback_observation() -> None:
    observer = RecordingObserver()

    output = run_llm_analysis_graph(
        SequentialAnalyzer((_incorrect_draft(), _incorrect_draft())),
        DEMO_CVE_ID,
        observer=observer,
    )

    assert output["analysis_source"] == "oracle_fallback"
    assert len(observer.observations) == 1
    observation = observer.observations[0]
    assert observation.analysis_source == "oracle_fallback"
    assert observation.validation_passed is False
    assert observation.analysis_attempts == 2
    assert observation.model_calls == 2
    assert observation.requires_human_review is True


def test_failed_graph_execution_emits_no_completed_observation() -> None:
    observer = RecordingObserver()

    with pytest.raises(RuntimeError, match="controlled analyzer failure"):
        run_llm_analysis_graph(
            FailingAnalyzer(),
            DEMO_CVE_ID,
            observer=observer,
        )

    assert observer.observations == []
