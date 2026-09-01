"""Tests for the native LlamaIndex evaluator-optimizer Workflow."""

import asyncio

from agentic_lab.adapters.fixtures.demo import (
    DEMO_CVE_ID,
    load_asset_inventory,
    load_security_policy,
    load_vulnerability_evidence,
)
from agentic_lab.adapters.llamaindex.analyzer import LlamaIndexUsage
from agentic_lab.adapters.llamaindex.workflow import (
    LlamaIndexValidatedAnalysisWorkflow,
    LlamaIndexWorkflowRuntime,
    ValidatedAnalysisStartEvent,
)
from agentic_lab.application.contracts import AssetAssessment, LLMAnalysisDraft
from agentic_lab.application.evidence import (
    AnalysisEvidenceBundle,
    AssetInventoryItem,
    VulnerabilityEvidence,
)
from agentic_lab.application.validated_analysis import FALLBACK_RECOMMENDATION


class SequenceAnalyzer:
    """Return deterministic drafts while recording evaluator feedback."""

    def __init__(self, drafts: list[LLMAnalysisDraft]) -> None:
        self._drafts = drafts
        self.calls: list[str | None] = []

    def analyze(
        self,
        vulnerability: VulnerabilityEvidence,
        assets: tuple[AssetInventoryItem, ...],
        feedback: str | None = None,
    ) -> LLMAnalysisDraft:
        assert vulnerability["cve_id"] == DEMO_CVE_ID
        assert len(assets) == 2
        self.calls.append(feedback)
        return self._drafts[len(self.calls) - 1]


class StubUsageRunner:
    """Provide structured drafts and isolated telemetry without network calls."""

    def __init__(self, drafts: list[LLMAnalysisDraft]) -> None:
        self._drafts = drafts
        self.calls: list[tuple[str, str]] = []

    def run(self, system_prompt: str, user_prompt: str) -> LLMAnalysisDraft:
        self.calls.append((system_prompt, user_prompt))
        return self._drafts[len(self.calls) - 1]

    def consume_usage(self) -> LlamaIndexUsage:
        model_calls = len(self.calls)
        return LlamaIndexUsage(
            input_tokens=500 * model_calls,
            output_tokens=100 * model_calls,
            total_tokens=600 * model_calls,
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
                rationale="Version 4.1 is below the exclusive 4.2 fixed boundary.",
            ),
            AssetAssessment(
                asset_id="api-prod-02",
                status="not_affected",
                rationale="Version 4.4 is not below the affected boundary.",
            ),
        ),
        recommendation="Upgrade the affected production asset.",
        confidence=0.97,
    )


def _wrong_draft() -> LLMAnalysisDraft:
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
                rationale="Version 4.4 is outside the affected range.",
            ),
        ),
        recommendation="No action required.",
        confidence=0.6,
    )


def _run_workflow(
    analyzer: SequenceAnalyzer,
    *,
    max_attempts: int = 2,
):
    bundle = _evidence_bundle()
    workflow = LlamaIndexValidatedAnalysisWorkflow(analyzer)
    return asyncio.run(
        workflow.run(
            start_event=ValidatedAnalysisStartEvent(
                vulnerability=bundle["vulnerability"],
                assets=bundle["assets"],
                policy=bundle["policy"],
                max_attempts=max_attempts,
            )
        )
    )


def test_workflow_accepts_correct_first_draft_and_applies_policy() -> None:
    analyzer = SequenceAnalyzer([_correct_draft()])

    output = _run_workflow(analyzer)

    assert output.analysis_source == "llm"
    assert output.validation_passed is True
    assert output.analysis_attempts == 1
    assert output.result.requires_human_review is True
    assert [asset.status for asset in output.result.assets] == [
        "affected",
        "not_affected",
    ]
    assert analyzer.calls == [None]


def test_workflow_retries_with_evaluator_feedback_and_recovers() -> None:
    analyzer = SequenceAnalyzer([_wrong_draft(), _correct_draft()])

    output = _run_workflow(analyzer)

    assert output.analysis_source == "llm"
    assert output.validation_passed is True
    assert output.analysis_attempts == 2
    assert len(analyzer.calls) == 2
    assert analyzer.calls[0] is None
    assert analyzer.calls[1] is not None
    assert "api-prod-01" in analyzer.calls[1]
    assert "deterministic oracle" not in analyzer.calls[1]


def test_workflow_falls_back_after_two_invalid_drafts() -> None:
    analyzer = SequenceAnalyzer([_wrong_draft(), _wrong_draft()])

    output = _run_workflow(analyzer)

    assert output.analysis_source == "oracle_fallback"
    assert output.validation_passed is False
    assert output.analysis_attempts == 2
    assert output.result.confidence == 1.0
    assert output.result.recommendation == FALLBACK_RECOMMENDATION
    assert [asset.status for asset in output.result.assets] == [
        "affected",
        "not_affected",
    ]
    assert len(analyzer.calls) == 2


def test_workflow_respects_single_attempt_limit() -> None:
    analyzer = SequenceAnalyzer([_wrong_draft()])

    output = _run_workflow(analyzer, max_attempts=1)

    assert output.analysis_source == "oracle_fallback"
    assert output.analysis_attempts == 1
    assert analyzer.calls == [None]


def test_runtime_returns_workflow_output_with_isolated_usage() -> None:
    runner = StubUsageRunner([_wrong_draft(), _correct_draft()])

    def runner_factory(model_name: str) -> StubUsageRunner:
        assert model_name == "openai:gpt-5.6-luna"
        return runner

    runtime = LlamaIndexWorkflowRuntime(
        "openai:gpt-5.6-luna",
        runner_factory=runner_factory,
    )

    execution = runtime.run(_evidence_bundle())

    assert execution.output.analysis_source == "llm"
    assert execution.output.analysis_attempts == 2
    assert execution.usage.model_calls == 2
    assert execution.usage.input_tokens == 1000
    assert execution.usage.output_tokens == 200
    assert execution.usage.total_tokens == 1200
    assert len(runner.calls) == 2
    assert "deterministic evaluator rejected" in runner.calls[1][1]


def test_runtime_rejects_invalid_attempt_limit_before_creating_runner() -> None:
    calls: list[str] = []

    def runner_factory(model_name: str) -> StubUsageRunner:
        calls.append(model_name)
        return StubUsageRunner([_correct_draft()])

    runtime = LlamaIndexWorkflowRuntime(
        "openai:gpt-5.6-luna",
        runner_factory=runner_factory,
    )

    try:
        runtime.run(_evidence_bundle(), max_attempts=0)
    except ValueError as exc:
        assert str(exc) == "max_attempts must be at least 1"
    else:
        raise AssertionError("Expected max_attempts=0 to be rejected")

    assert calls == []
