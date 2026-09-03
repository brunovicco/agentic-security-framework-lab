"""Provider-free tests for reviewed adversarial v2 baseline promotion."""

import hashlib
import json
from pathlib import Path
from runpy import run_path
from typing import Any

import pytest

_SCRIPT = run_path(
    str(
        Path(__file__).parents[2]
        / "scripts"
        / "promote_adversarial_v2_workflow_baselines.py"
    )
)
promote_workflow: Any = _SCRIPT["promote_workflow"]
validate_candidate: Any = _SCRIPT["validate_candidate"]

_WORKFLOW = "crewai-flow"
_GENERATED_AT = "2026-09-03T18:31:04.260957+00:00"
_PATTERN = "flow_direct_llm_evaluator_optimizer_adversarial_v2_evidence_plane"


def _candidate_payload() -> dict[str, Any]:
    runs = [
        {
            "scenario_id": f"scenario-{index // 3}",
            "iteration": (index % 3) + 1,
            "model": "openai:gpt-5.6-luna",
            "task_match": True,
            "security_passed": True,
            "unsafe_acceptance": False,
        }
        for index in range(18)
    ]
    return {
        "schema_version": "1",
        "suite_version": "2",
        "artifact_type": "baseline_candidate",
        "official_baseline": False,
        "review_status": "pending_manual_trace_review",
        "generated_at_utc": _GENERATED_AT,
        "workflow": _WORKFLOW,
        "framework": "crewai",
        "pattern": _PATTERN,
        "model": "openai:gpt-5.6-luna",
        "sampling": "provider_default",
        "repetitions_per_scenario": 3,
        "scenario_count": 6,
        "runs": runs,
        "scenario_summaries": [{} for _ in range(6)],
        "baseline_assessment": {
            "passed": True,
            "runs": 18,
            "failures": [],
        },
    }


def _write_candidate(root: Path, payload: dict[str, Any]) -> tuple[Path, Path]:
    candidate_dir = root / _WORKFLOW
    candidate_dir.mkdir(parents=True)
    json_path = candidate_dir / "latest.json"
    markdown_path = candidate_dir / "latest.md"
    json_path.write_text(json.dumps(payload, indent=2) + "\n")
    markdown_path.write_text(
        "# CrewAI Flow Adversarial Security Evaluation v2 Baseline Candidate\n\n"
        "Evidence-plane indirect prompt-injection suite.\n\n"
        "## Baseline candidate status\n\n"
        "Pending manual review.\n"
    )
    return json_path, markdown_path


def _manifest(candidate_path: Path, *, approved: bool = True) -> dict[str, Any]:
    digest = hashlib.sha256(candidate_path.read_bytes()).hexdigest()
    return {
        "review_status": "accepted_manual_trace_review",
        "reviewed_at_utc": "2026-09-03T18:37:49.671368+00:00",
        "review_record": "docs/security/ADVERSARIAL_V2_CROSS_FRAMEWORK_BASELINE_REVIEW.md",
        "reviewed_against_repository_commit": "16ec342",
        "scenario_fixture_blob_sha": "fixture-sha",
        "adversarial_evaluator_blob_sha": "evaluator-sha",
        "candidates": {
            _WORKFLOW: {
                "approved": approved,
                "framework": "crewai",
                "pattern": _PATTERN,
                "generated_at_utc": _GENERATED_AT,
                "sha256": digest,
            }
        },
    }


def test_promote_workflow_requires_exact_reviewed_hash_and_preserves_candidate(
    tmp_path: Path,
) -> None:
    candidate_root = tmp_path / "candidates"
    baseline_root = tmp_path / "baselines"
    payload = _candidate_payload()
    candidate_path, candidate_markdown_path = _write_candidate(candidate_root, payload)
    original_json = candidate_path.read_text()
    original_markdown = candidate_markdown_path.read_text()
    manifest = _manifest(candidate_path)

    official_json_path, official_markdown_path = promote_workflow(
        workflow=_WORKFLOW,
        manifest=manifest,
        candidate_root=candidate_root,
        baseline_root=baseline_root,
    )

    official = json.loads(official_json_path.read_text())
    markdown = official_markdown_path.read_text()
    assert official["artifact_type"] == "baseline"
    assert official["official_baseline"] is True
    assert official["review_status"] == "accepted_manual_trace_review"
    assert official["promotion"]["source_candidate_sha256"] == manifest["candidates"][
        _WORKFLOW
    ]["sha256"]
    assert "Baseline Candidate" not in markdown
    assert "official adversarial v2 baseline" in markdown
    assert candidate_path.read_text() == original_json
    assert candidate_markdown_path.read_text() == original_markdown


def test_validate_candidate_rejects_hash_mismatch(tmp_path: Path) -> None:
    candidate_root = tmp_path / "candidates"
    payload = _candidate_payload()
    candidate_path, _ = _write_candidate(candidate_root, payload)
    manifest = _manifest(candidate_path)
    manifest["candidates"][_WORKFLOW]["sha256"] = "0" * 64

    with pytest.raises(ValueError, match="hash mismatch"):
        validate_candidate(
            workflow=_WORKFLOW,
            candidate_path=candidate_path,
            candidate=payload,
            manifest=manifest,
        )


def test_validate_candidate_rejects_unapproved_workflow(tmp_path: Path) -> None:
    candidate_root = tmp_path / "candidates"
    payload = _candidate_payload()
    candidate_path, _ = _write_candidate(candidate_root, payload)
    manifest = _manifest(candidate_path, approved=False)

    with pytest.raises(ValueError, match="not approved"):
        validate_candidate(
            workflow=_WORKFLOW,
            candidate_path=candidate_path,
            candidate=payload,
            manifest=manifest,
        )


def test_validate_candidate_rejects_invariant_failure_even_when_hash_is_approved(
    tmp_path: Path,
) -> None:
    candidate_root = tmp_path / "candidates"
    payload = _candidate_payload()
    payload["runs"][7]["unsafe_acceptance"] = True
    candidate_path, _ = _write_candidate(candidate_root, payload)
    manifest = _manifest(candidate_path)

    with pytest.raises(ValueError, match="unsafe acceptance"):
        validate_candidate(
            workflow=_WORKFLOW,
            candidate_path=candidate_path,
            candidate=payload,
            manifest=manifest,
        )
