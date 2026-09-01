"""Adversarial v2 contract for evidence-plane prompt-injection scenarios."""

from dataclasses import dataclass

from agentic_lab.application.adversarial_evaluation import AdversarialEvaluationScenario
from agentic_lab.application.evidence import EvidenceDocument


@dataclass(frozen=True, slots=True)
class AdversarialEvidenceScenario(AdversarialEvaluationScenario):
    """Extend the shared adversarial scenario with textual evidence documents."""

    documents: tuple[EvidenceDocument, ...] = ()
