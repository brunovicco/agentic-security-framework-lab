"""State schemas for LangGraph vulnerability-analysis workflows."""

from operator import add
from typing import Annotated, Literal, NotRequired, TypedDict

from agentic_lab.application.contracts import (
    AnalysisResult,
    AssetAssessment,
    LLMAnalysisDraft,
)
from agentic_lab.application.evidence import (
    AnalysisEvidenceBundle,
    AssetInventoryItem,
    SecurityPolicy,
    VulnerabilityEvidence,
)
from agentic_lab.application.validated_analysis import AnalysisAttemptEvidence


class AnalysisGraphInput(TypedDict):
    """Public input accepted by the deterministic analysis graph."""

    cve_id: str


class LLMAnalysisGraphInput(TypedDict):
    """Public input accepted by the validated LLM analysis graph."""

    cve_id: str
    evidence_bundle: NotRequired[AnalysisEvidenceBundle]


class AnalysisGraphOutput(TypedDict):
    """Public output returned by the deterministic analysis graph."""

    result: AnalysisResult


class LLMAnalysisGraphOutput(TypedDict):
    """Public output returned by the validated LLM analysis graph."""

    result: AnalysisResult
    analysis_source: Literal["llm", "oracle_fallback"]
    validation_passed: bool
    validation_reason: str
    analysis_attempts: int
    attempt_trace: tuple[AnalysisAttemptEvidence, ...]


class AnalysisGraphState(TypedDict, total=False):
    """Internal state shared by vulnerability-analysis graph nodes."""

    cve_id: str
    evidence_bundle: AnalysisEvidenceBundle

    vulnerability: VulnerabilityEvidence
    assets: tuple[AssetInventoryItem, ...]
    policy: SecurityPolicy

    llm_draft: LLMAnalysisDraft
    analysis_attempts: int
    attempt_trace: Annotated[tuple[AnalysisAttemptEvidence, ...], add]

    validation_passed: bool
    validation_reason: str
    validation_feedback: str

    analysis_source: Literal["llm", "oracle_fallback"]

    assessments: tuple[AssetAssessment, ...]
    recommendation: str
    confidence: float

    requires_human_review: bool
    result: AnalysisResult
