"""LlamaIndex Workflow implementation of validated vulnerability analysis."""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol, cast

from pydantic import Field
from workflows import Workflow, step
from workflows.events import Event, StartEvent, StopEvent

from agentic_lab.adapters.gateway import gateway_model_alias
from agentic_lab.adapters.llamaindex.analyzer import (
    LlamaIndexAnalysisRunner,
    LlamaIndexRuntime,
    LlamaIndexUsage,
    LlamaIndexVulnerabilityAnalyzer,
)
from agentic_lab.application.analyzer import VulnerabilityAnalyzer
from agentic_lab.application.contracts import LLMAnalysisDraft
from agentic_lab.application.evidence import (
    AnalysisEvidenceBundle,
    AssetInventoryItem,
    SecurityPolicy,
    VulnerabilityEvidence,
)
from agentic_lab.application.evidence_document_analyzer import bind_evidence_documents
from agentic_lab.application.oracle import assess_assets_deterministically
from agentic_lab.application.validated_analysis import (
    DEFAULT_MAX_ANALYSIS_ATTEMPTS,
    FALLBACK_RECOMMENDATION,
    AnalysisAttemptEvidence,
    ValidatedAnalysisOutput,
    build_analysis_result,
    evaluate_human_review_policy,
    validate_analysis_draft,
)


class _UsageAwareAnalysisRunner(LlamaIndexAnalysisRunner, Protocol):
    """Structured analysis runner that also exposes isolated usage telemetry."""

    def consume_usage(self) -> LlamaIndexUsage:
        """Return usage accumulated by the current execution and reset it."""
        ...


RunnerFactory = Callable[[], _UsageAwareAnalysisRunner]


class ValidatedAnalysisStartEvent(StartEvent):
    """Start one LlamaIndex evaluator-optimizer execution."""

    vulnerability: VulnerabilityEvidence
    assets: tuple[AssetInventoryItem, ...]
    policy: SecurityPolicy
    max_attempts: int = Field(default=DEFAULT_MAX_ANALYSIS_ATTEMPTS, ge=1)


class AnalysisDraftEvent(Event):
    """Carry one LLM draft to deterministic validation."""

    vulnerability: VulnerabilityEvidence
    assets: tuple[AssetInventoryItem, ...]
    policy: SecurityPolicy
    max_attempts: int
    analysis_attempts: int
    input_feedback: str | None
    attempt_trace: tuple[AnalysisAttemptEvidence, ...]
    draft: LLMAnalysisDraft


class RetryAnalysisEvent(Event):
    """Request another bounded LLM attempt with evaluator feedback."""

    vulnerability: VulnerabilityEvidence
    assets: tuple[AssetInventoryItem, ...]
    policy: SecurityPolicy
    max_attempts: int
    analysis_attempts: int
    feedback: str
    attempt_trace: tuple[AnalysisAttemptEvidence, ...]


class AcceptedAnalysisEvent(Event):
    """Carry a deterministically accepted LLM draft to final policy evaluation."""

    vulnerability: VulnerabilityEvidence
    assets: tuple[AssetInventoryItem, ...]
    policy: SecurityPolicy
    analysis_attempts: int
    validation_reason: str
    attempt_trace: tuple[AnalysisAttemptEvidence, ...]
    draft: LLMAnalysisDraft


class FallbackAnalysisEvent(Event):
    """Request deterministic oracle fallback after exhausting LLM attempts."""

    vulnerability: VulnerabilityEvidence
    assets: tuple[AssetInventoryItem, ...]
    policy: SecurityPolicy
    analysis_attempts: int
    validation_reason: str
    attempt_trace: tuple[AnalysisAttemptEvidence, ...]


@dataclass(frozen=True, slots=True)
class LlamaIndexWorkflowExecution:
    """Return one validated Workflow result with framework LLM usage."""

    output: ValidatedAnalysisOutput
    usage: LlamaIndexUsage


class LlamaIndexValidatedAnalysisWorkflow(Workflow):
    """Orchestrate bounded LLM reasoning and deterministic controls with events."""

    def __init__(
        self,
        analyzer: VulnerabilityAnalyzer,
        *,
        timeout: float | None = 45.0,
    ) -> None:
        """Create a fresh workflow around an application-compatible analyzer."""
        super().__init__(timeout=timeout, verbose=False)
        self._analyzer = analyzer

    @step
    async def analyze_once(self, ev: ValidatedAnalysisStartEvent) -> AnalysisDraftEvent:
        """Execute the first structured LLM analysis attempt."""
        draft = self._analyzer.analyze(
            vulnerability=ev.vulnerability,
            assets=ev.assets,
            feedback=None,
        )
        return AnalysisDraftEvent(
            vulnerability=ev.vulnerability,
            assets=ev.assets,
            policy=ev.policy,
            max_attempts=ev.max_attempts,
            analysis_attempts=1,
            input_feedback=None,
            attempt_trace=(),
            draft=draft,
        )

    @step
    async def evaluate_draft(
        self,
        ev: AnalysisDraftEvent,
    ) -> AcceptedAnalysisEvent | RetryAnalysisEvent | FallbackAnalysisEvent:
        """Route an LLM draft using the shared deterministic applicability evaluator."""
        validation = validate_analysis_draft(
            vulnerability=ev.vulnerability,
            assets=ev.assets,
            draft=ev.draft,
        )
        attempt_trace = (
            *ev.attempt_trace,
            AnalysisAttemptEvidence(
                attempt=ev.analysis_attempts,
                input_feedback=ev.input_feedback,
                draft=ev.draft,
                validation_passed=validation.passed,
                validation_reason=validation.reason,
                validation_feedback=validation.feedback,
            ),
        )

        if validation.passed:
            return AcceptedAnalysisEvent(
                vulnerability=ev.vulnerability,
                assets=ev.assets,
                policy=ev.policy,
                analysis_attempts=ev.analysis_attempts,
                validation_reason=validation.reason,
                attempt_trace=attempt_trace,
                draft=ev.draft,
            )

        if ev.analysis_attempts < ev.max_attempts:
            return RetryAnalysisEvent(
                vulnerability=ev.vulnerability,
                assets=ev.assets,
                policy=ev.policy,
                max_attempts=ev.max_attempts,
                analysis_attempts=ev.analysis_attempts,
                feedback=validation.feedback,
                attempt_trace=attempt_trace,
            )

        return FallbackAnalysisEvent(
            vulnerability=ev.vulnerability,
            assets=ev.assets,
            policy=ev.policy,
            analysis_attempts=ev.analysis_attempts,
            validation_reason=validation.reason,
            attempt_trace=attempt_trace,
        )

    @step
    async def retry_analysis(self, ev: RetryAnalysisEvent) -> AnalysisDraftEvent:
        """Retry structured reasoning with deterministic evaluator feedback."""
        next_attempt = ev.analysis_attempts + 1
        draft = self._analyzer.analyze(
            vulnerability=ev.vulnerability,
            assets=ev.assets,
            feedback=ev.feedback,
        )
        return AnalysisDraftEvent(
            vulnerability=ev.vulnerability,
            assets=ev.assets,
            policy=ev.policy,
            max_attempts=ev.max_attempts,
            analysis_attempts=next_attempt,
            input_feedback=ev.feedback,
            attempt_trace=ev.attempt_trace,
            draft=draft,
        )

    @step
    async def finalize_llm_analysis(self, ev: AcceptedAnalysisEvent) -> StopEvent:
        """Apply deterministic human-review policy to an accepted LLM draft."""
        requires_human_review = evaluate_human_review_policy(
            vulnerability=ev.vulnerability,
            assets=ev.assets,
            policy=ev.policy,
            assessments=ev.draft.assets,
        )
        result = build_analysis_result(
            vulnerability=ev.vulnerability,
            assessments=ev.draft.assets,
            recommendation=ev.draft.recommendation,
            confidence=ev.draft.confidence,
            requires_human_review=requires_human_review,
        )
        return StopEvent(
            result=ValidatedAnalysisOutput(
                result=result,
                analysis_source="llm",
                validation_passed=True,
                validation_reason=ev.validation_reason,
                analysis_attempts=ev.analysis_attempts,
                attempt_trace=ev.attempt_trace,
            )
        )

    @step
    async def finalize_oracle_fallback(self, ev: FallbackAnalysisEvent) -> StopEvent:
        """Fail closed to deterministic assessment after bounded LLM attempts."""
        assessments = assess_assets_deterministically(
            vulnerability=ev.vulnerability,
            assets=ev.assets,
        )
        requires_human_review = evaluate_human_review_policy(
            vulnerability=ev.vulnerability,
            assets=ev.assets,
            policy=ev.policy,
            assessments=assessments,
        )
        result = build_analysis_result(
            vulnerability=ev.vulnerability,
            assessments=assessments,
            recommendation=FALLBACK_RECOMMENDATION,
            confidence=1.0,
            requires_human_review=requires_human_review,
        )
        return StopEvent(
            result=ValidatedAnalysisOutput(
                result=result,
                analysis_source="oracle_fallback",
                validation_passed=False,
                validation_reason=ev.validation_reason,
                analysis_attempts=ev.analysis_attempts,
                attempt_trace=ev.attempt_trace,
            )
        )


class LlamaIndexWorkflowRuntime:
    """Execute the evaluator-optimizer using native LlamaIndex Workflow events."""

    def __init__(
        self,
        model_alias: str | None = None,
        *,
        runner_factory: RunnerFactory = LlamaIndexRuntime,
    ) -> None:
        """Accept only the governed alias and store no provider model identity."""
        if model_alias is not None and model_alias != gateway_model_alias():
            raise ValueError("LlamaIndex Workflow accepts only the governed gateway alias")
        self._runner_factory = runner_factory

    async def arun(
        self,
        evidence_bundle: AnalysisEvidenceBundle,
        max_attempts: int = DEFAULT_MAX_ANALYSIS_ATTEMPTS,
    ) -> LlamaIndexWorkflowExecution:
        """Execute one fresh Workflow and return validated output plus isolated usage."""
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")

        runner = self._runner_factory()
        analyzer = bind_evidence_documents(
            LlamaIndexVulnerabilityAnalyzer(runner),
            evidence_bundle,
        )
        workflow = LlamaIndexValidatedAnalysisWorkflow(analyzer)
        raw_output = cast(
            object,
            await workflow.run(
                start_event=ValidatedAnalysisStartEvent(
                    vulnerability=evidence_bundle["vulnerability"],
                    assets=evidence_bundle["assets"],
                    policy=evidence_bundle["policy"],
                    max_attempts=max_attempts,
                )
            ),
        )

        if not isinstance(raw_output, ValidatedAnalysisOutput):
            raise RuntimeError("LlamaIndex Workflow ended without a validated analysis result")

        return LlamaIndexWorkflowExecution(
            output=raw_output,
            usage=runner.consume_usage(),
        )

    def run(
        self,
        evidence_bundle: AnalysisEvidenceBundle,
        max_attempts: int = DEFAULT_MAX_ANALYSIS_ATTEMPTS,
    ) -> LlamaIndexWorkflowExecution:
        """Run from synchronous code; async applications should call arun()."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(
                self.arun(
                    evidence_bundle=evidence_bundle,
                    max_attempts=max_attempts,
                )
            )

        raise RuntimeError(
            "LlamaIndexWorkflowRuntime.run() cannot be used inside an active event loop; use arun()"
        )
