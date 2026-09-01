"""Adversarial v2 contract for evidence-plane prompt-injection scenarios."""

from dataclasses import dataclass

from agentic_lab.application.adversarial_evaluation import AdversarialEvaluationScenario
from agentic_lab.application.evidence import AnalysisEvidenceBundle, EvidenceDocument


@dataclass(frozen=True, slots=True)
class AdversarialEvidenceScenario(AdversarialEvaluationScenario):
    """Extend the shared adversarial scenario with textual evidence documents."""

    documents: tuple[EvidenceDocument, ...] = ()


def build_adversarial_v2_evidence_bundle(
    scenario: AdversarialEvidenceScenario,
) -> AnalysisEvidenceBundle:
    """Convert a v2 scenario into executable structured and textual evidence."""
    return {
        "vulnerability": scenario.vulnerability,
        "assets": scenario.assets,
        "policy": scenario.policy,
        "documents": scenario.documents,
    }
