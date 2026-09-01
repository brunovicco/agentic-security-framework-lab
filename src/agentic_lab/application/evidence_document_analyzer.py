"""Bind textual evidence documents to a framework analyzer without widening core ports."""

from dataclasses import dataclass
from typing import Protocol

from agentic_lab.application.contracts import LLMAnalysisDraft
from agentic_lab.application.evidence import (
    AnalysisEvidenceBundle,
    AssetInventoryItem,
    EvidenceDocument,
    VulnerabilityEvidence,
)


class EvidenceDocumentAnalyzer(Protocol):
    """Analyzer extension that can consume explicitly untrusted textual evidence."""

    def analyze(
        self,
        vulnerability: VulnerabilityEvidence,
        assets: tuple[AssetInventoryItem, ...],
        feedback: str | None = None,
        documents: tuple[EvidenceDocument, ...] = (),
    ) -> LLMAnalysisDraft:
        """Analyze structured evidence plus optional textual evidence documents."""
        ...


@dataclass(frozen=True, slots=True)
class EvidenceDocumentBoundAnalyzer:
    """Expose the canonical analyzer port while binding one immutable document set."""

    delegate: EvidenceDocumentAnalyzer
    documents: tuple[EvidenceDocument, ...]

    def analyze(
        self,
        vulnerability: VulnerabilityEvidence,
        assets: tuple[AssetInventoryItem, ...],
        feedback: str | None = None,
    ) -> LLMAnalysisDraft:
        """Forward every attempt with the same application-supplied documents."""
        return self.delegate.analyze(
            vulnerability=vulnerability,
            assets=assets,
            feedback=feedback,
            documents=self.documents,
        )


def bind_evidence_documents(
    analyzer: EvidenceDocumentAnalyzer,
    evidence_bundle: AnalysisEvidenceBundle,
) -> EvidenceDocumentBoundAnalyzer:
    """Bind documents from one evidence bundle without exposing them to control logic."""
    return EvidenceDocumentBoundAnalyzer(
        delegate=analyzer,
        documents=evidence_bundle.get("documents", ()),
    )
