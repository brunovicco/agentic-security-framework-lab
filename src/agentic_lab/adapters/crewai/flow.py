"""CrewAI Flow implementation of the validated vulnerability-analysis workflow."""

from dataclasses import dataclass
from typing import Protocol, cast

from crewai.flow.flow import Flow, listen, router, start
from pydantic import BaseModel, Field

from agentic_lab.adapters.crewai.analyzer import (
    CREWAI_SECURITY_SYSTEM_PROMPT,
    CrewAIUsage,
    build_crewai_analysis_task_description,
)
from agentic_lab.adapters.crewai.model import create_crewai_llm
from agentic_lab.application.contracts import AnalysisResult, LLMAnalysisDraft
from agentic_lab.application.evidence import (
    AnalysisEvidenceBundle,
    AssetInventoryItem,
    EvidenceDocument,
    SecurityPolicy,
    VulnerabilityEvidence,
)
from agentic_lab.application.oracle import assess_assets_deterministically
from agentic_lab.application.validated_analysis import (
    DEFAULT_MAX_ANALYSIS_ATTEMPTS,
    FALLBACK_RECOMMENDATION,
    AnalysisAttemptEvidence,
    AnalysisSource,
    ValidatedAnalysisOutput,
    build_analysis_result,
    evaluate_human_review_policy,
    validate_analysis_draft,
)

_ACCEPTED_ROUTE = "accepted"
_RETRY_ROUTE = "retry"
_FALLBACK_ROUTE = "fallback"


class _StructuredLLM(Protocol):
    """Minimum CrewAI LLM surface required by the direct Flow path."""

    def call(
        self,
        messages: str | list[dict[str, str]],
        *,
        response_model: type[BaseModel],
    ) -> object:
        """Call the model and return structured output."""
        ...


class _FlowUsageMetrics(Protocol):
    """Minimum CrewAI Flow usage surface required for benchmark telemetry."""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    successful_requests: int


class CrewAIValidatedFlowState(BaseModel):
    """Structured mutable state for the CrewAI evaluator-optimizer Flow."""

    model_name: str
    vulnerability: VulnerabilityEvidence
    assets: tuple[AssetInventoryItem, ...]
    policy: SecurityPolicy
    documents: tuple[EvidenceDocument, ...] = ()
    max_attempts: int = Field(default=DEFAULT_MAX_ANALYSIS_ATTEMPTS, ge=1)
    analysis_attempts: int = 0
    draft: LLMAnalysisDraft | None = None
    feedback: str | None = None
    validation_passed: bool = False
    validation_reason: str = ""
    analysis_source: AnalysisSource | None = None
    result: AnalysisResult | None = None
    attempt_trace: tuple[AnalysisAttemptEvidence, ...] = ()


@dataclass(frozen=True, slots=True)
class CrewAIFlowExecution:
    """Return one validated Flow result with framework-reported usage."""

    output: ValidatedAnalysisOutput
    usage: CrewAIUsage


def _create_structured_llm(_model_name: str) -> _StructuredLLM:
    """Create the CrewAI structured client through the governed gateway boundary."""
    return cast(_StructuredLLM, create_crewai_llm())


class CrewAIValidatedAnalysisFlow(Flow[CrewAIValidatedFlowState]):
    """Orchestrate analysis, deterministic validation, retry, and fallback in CrewAI Flow."""

    suppress_flow_events: bool = True

    def _require_draft(self) -> LLMAnalysisDraft:
        draft = self.state.draft
        if draft is None:
            raise RuntimeError("CrewAI Flow validation requires an LLM analysis draft")
        return draft

    def _call_structured_llm(self) -> LLMAnalysisDraft:
        llm = _create_structured_llm(self.state.model_name)
        task_description = build_crewai_analysis_task_description(
            vulnerability=self.state.vulnerability,
            assets=self.state.assets,
            feedback=self.state.feedback,
            documents=self.state.documents,
        )
        messages = [
            {
                "role": "system",
                "content": CREWAI_SECURITY_SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": task_description,
            },
        ]
        raw_output = llm.call(
            messages,
            response_model=LLMAnalysisDraft,
        )
        return LLMAnalysisDraft.model_validate(raw_output)

    def _route_current_draft(self) -> str:
        draft = self._require_draft()
        input_feedback = self.state.feedback
        validation = validate_analysis_draft(
            vulnerability=self.state.vulnerability,
            assets=self.state.assets,
            draft=draft,
        )
        self.state.attempt_trace = (
            *self.state.attempt_trace,
            AnalysisAttemptEvidence(
                attempt=self.state.analysis_attempts,
                input_feedback=input_feedback,
                draft=draft,
                validation_passed=validation.passed,
                validation_reason=validation.reason,
                validation_feedback=validation.feedback,
            ),
        )
        self.state.validation_passed = validation.passed
        self.state.validation_reason = validation.reason

        if validation.passed:
            self.state.feedback = None
            return _ACCEPTED_ROUTE

        self.state.feedback = validation.feedback
        if self.state.analysis_attempts < self.state.max_attempts:
            return _RETRY_ROUTE

        return _FALLBACK_ROUTE

    @start()
    def analyze_once(self) -> LLMAnalysisDraft:
        """Execute the first direct structured LLM analysis."""
        self.state.analysis_attempts += 1
        self.state.draft = self._call_structured_llm()
        return self._require_draft()

    @router(analyze_once)
    def route_first_analysis(self) -> str:
        """Accept, retry, or fall back after the first deterministic evaluation."""
        return self._route_current_draft()

    @listen(_RETRY_ROUTE)
    def retry_analysis(self) -> LLMAnalysisDraft:
        """Retry analysis using application-owned deterministic evaluator feedback."""
        self.state.analysis_attempts += 1
        self.state.draft = self._call_structured_llm()
        return self._require_draft()

    @router(retry_analysis)
    def route_retry_analysis(self) -> str:
        """Re-evaluate each retry and continue only within the bounded attempt limit."""
        return self._route_current_draft()

    @listen(_ACCEPTED_ROUTE)
    def finalize_llm_analysis(self) -> AnalysisResult:
        """Apply deterministic policy to an accepted LLM draft."""
        draft = self._require_draft()
        requires_human_review = evaluate_human_review_policy(
            vulnerability=self.state.vulnerability,
            assets=self.state.assets,
            policy=self.state.policy,
            assessments=draft.assets,
        )
        result = build_analysis_result(
            vulnerability=self.state.vulnerability,
            assessments=draft.assets,
            recommendation=draft.recommendation,
            confidence=draft.confidence,
            requires_human_review=requires_human_review,
        )
        self.state.analysis_source = "llm"
        self.state.result = result
        return result

    @listen(_FALLBACK_ROUTE)
    def finalize_oracle_fallback(self) -> AnalysisResult:
        """Fail closed to the deterministic oracle after exhausting LLM attempts."""
        assessments = assess_assets_deterministically(
            vulnerability=self.state.vulnerability,
            assets=self.state.assets,
        )
        requires_human_review = evaluate_human_review_policy(
            vulnerability=self.state.vulnerability,
            assets=self.state.assets,
            policy=self.state.policy,
            assessments=assessments,
        )
        result = build_analysis_result(
            vulnerability=self.state.vulnerability,
            assessments=assessments,
            recommendation=FALLBACK_RECOMMENDATION,
            confidence=1.0,
            requires_human_review=requires_human_review,
        )
        self.state.analysis_source = "oracle_fallback"
        self.state.result = result
        return result


class CrewAIFlowRuntime:
    """Execute the direct-LLM evaluator-optimizer through CrewAI Flow."""

    def __init__(self, model_name: str) -> None:
        """Store transitional report metadata; provider selection is gateway-owned."""
        self._model_name = model_name

    def run(
        self,
        evidence_bundle: AnalysisEvidenceBundle,
        max_attempts: int = DEFAULT_MAX_ANALYSIS_ATTEMPTS,
    ) -> CrewAIFlowExecution:
        """Execute one Flow and return validated output plus per-kickoff telemetry."""
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")

        flow = CrewAIValidatedAnalysisFlow(
            initial_state=CrewAIValidatedFlowState(
                model_name=self._model_name,
                vulnerability=evidence_bundle["vulnerability"],
                assets=evidence_bundle["assets"],
                policy=evidence_bundle["policy"],
                documents=evidence_bundle.get("documents", ()),
                max_attempts=max_attempts,
            )
        )
        cast(object, flow.kickoff())

        result = flow.state.result
        analysis_source = flow.state.analysis_source
        if result is None or analysis_source is None:
            raise RuntimeError("CrewAI Flow ended without a validated analysis result")

        output = ValidatedAnalysisOutput(
            result=result,
            analysis_source=analysis_source,
            validation_passed=flow.state.validation_passed,
            validation_reason=flow.state.validation_reason,
            analysis_attempts=flow.state.analysis_attempts,
            attempt_trace=flow.state.attempt_trace,
        )
        metrics = cast(_FlowUsageMetrics, flow.usage_metrics)
        usage = CrewAIUsage(
            input_tokens=metrics.prompt_tokens,
            output_tokens=metrics.completion_tokens,
            total_tokens=metrics.total_tokens,
            model_calls=metrics.successful_requests,
        )
        return CrewAIFlowExecution(
            output=output,
            usage=usage,
        )
