"""State schemas for LangGraph vulnerability-analysis workflows."""

from typing import Literal, TypedDict

from agentic_lab.application.contracts import (
    AnalysisResult,
    AssetAssessment,
    LLMAnalysisDraft,
)
from agentic_lab.application.evidence import (
    AssetInventoryItem,
    SecurityPolicy,
    VulnerabilityEvidence,
)


class AnalysisGraphInput(TypedDict):
    """Public input accepted by the vulnerability-analysis graph."""

    cve_id: str


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


class AnalysisGraphState(TypedDict, total=False):
    """Internal state shared by vulnerability-analysis graph nodes."""

    cve_id: str
    vulnerability: VulnerabilityEvidence
    assets: tuple[AssetInventoryItem, ...]
    policy: SecurityPolicy

    llm_draft: LLMAnalysisDraft
    analysis_attempts: int

    validation_passed: bool
    validation_reason: str
    validation_feedback: str

    analysis_source: Literal["llm", "oracle_fallback"]

    assessments: tuple[AssetAssessment, ...]
    recommendation: str
    confidence: float

    requires_human_review: bool
    result: AnalysisResult
