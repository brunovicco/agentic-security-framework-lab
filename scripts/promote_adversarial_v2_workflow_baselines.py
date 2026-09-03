"""Promote only manually reviewed adversarial v2 baseline candidates."""

import argparse
import hashlib
import json
from collections.abc import Mapping, Sequence
from copy import deepcopy
from pathlib import Path
from typing import Any, cast

_REVIEW_MANIFEST = Path(
    "docs/security/adversarial_v2_cross_framework_baseline_review.json"
)
_CANDIDATE_ROOT = Path("artifacts/adversarial-v2-candidates")
_BASELINE_ROOT = Path("artifacts/adversarial-v2")
_EXPECTED_SUITE_VERSION = "2"
_EXPECTED_MODEL = "openai:gpt-5.6-luna"
_EXPECTED_SAMPLING = "provider_default"
_EXPECTED_REPETITIONS = 3
_EXPECTED_SCENARIO_COUNT = 6
_EXPECTED_RUN_COUNT = _EXPECTED_REPETITIONS * _EXPECTED_SCENARIO_COUNT


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest of a persisted candidate artifact."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json_object(path: Path) -> dict[str, Any]:
    """Load one JSON object and reject non-object roots."""
    payload = json.loads(path.read_text())
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return cast(dict[str, Any], payload)


def load_review_manifest(path: Path = _REVIEW_MANIFEST) -> dict[str, Any]:
    """Load the machine-readable manual-review decision."""
    manifest = load_json_object(path)
    if manifest.get("review_status") != "accepted_manual_trace_review":
        raise ValueError("Review manifest is not an accepted manual trace review")
    return manifest


def _candidate_record(
    manifest: Mapping[str, Any],
    workflow: str,
) -> dict[str, Any]:
    candidates = manifest.get("candidates")
    if not isinstance(candidates, dict):
        raise ValueError("Review manifest candidates must be an object")
    record = candidates.get(workflow)
    if not isinstance(record, dict):
        raise ValueError(f"Workflow {workflow!r} is absent from the review manifest")
    typed = cast(dict[str, Any], record)
    if typed.get("approved") is not True:
        raise ValueError(f"Workflow {workflow!r} is not approved for promotion")
    return typed


def validate_candidate(
    *,
    workflow: str,
    candidate_path: Path,
    candidate: Mapping[str, Any],
    manifest: Mapping[str, Any],
) -> None:
    """Fail closed unless the exact manually reviewed candidate is present."""
    record = _candidate_record(manifest, workflow)
    expected_hash = record.get("sha256")
    observed_hash = sha256_file(candidate_path)
    if observed_hash != expected_hash:
        raise ValueError(
            f"Candidate hash mismatch for {workflow}: "
            f"expected {expected_hash}, observed {observed_hash}"
        )

    expected_metadata = {
        "schema_version": "1",
        "suite_version": _EXPECTED_SUITE_VERSION,
        "artifact_type": "baseline_candidate",
        "official_baseline": False,
        "review_status": "pending_manual_trace_review",
        "workflow": workflow,
        "framework": record.get("framework"),
        "pattern": record.get("pattern"),
        "model": _EXPECTED_MODEL,
        "sampling": _EXPECTED_SAMPLING,
        "repetitions_per_scenario": _EXPECTED_REPETITIONS,
        "scenario_count": _EXPECTED_SCENARIO_COUNT,
        "generated_at_utc": record.get("generated_at_utc"),
    }
    mismatches = [
        key
        for key, expected in expected_metadata.items()
        if candidate.get(key) != expected
    ]
    if mismatches:
        joined = ", ".join(mismatches)
        raise ValueError(f"Candidate metadata mismatch for {workflow}: {joined}")

    runs = candidate.get("runs")
    summaries = candidate.get("scenario_summaries")
    assessment = candidate.get("baseline_assessment")
    if not isinstance(runs, list) or len(runs) != _EXPECTED_RUN_COUNT:
        raise ValueError(f"Candidate {workflow} must contain {_EXPECTED_RUN_COUNT} runs")
    if not isinstance(summaries, list) or len(summaries) != _EXPECTED_SCENARIO_COUNT:
        raise ValueError(
            f"Candidate {workflow} must contain {_EXPECTED_SCENARIO_COUNT} scenario summaries"
        )
    if not isinstance(assessment, dict) or assessment.get("passed") is not True:
        raise ValueError(f"Candidate {workflow} did not pass its baseline assessment")
    if assessment.get("runs") != _EXPECTED_RUN_COUNT or assessment.get("failures") != []:
        raise ValueError(f"Candidate {workflow} has an inconsistent baseline assessment")

    for run in runs:
        if not isinstance(run, dict):
            raise ValueError(f"Candidate {workflow} contains a non-object run")
        if run.get("task_match") is not True:
            raise ValueError(f"Candidate {workflow} contains a task mismatch")
        if run.get("security_passed") is not True:
            raise ValueError(f"Candidate {workflow} contains a security failure")
        if run.get("unsafe_acceptance") is not False:
            raise ValueError(f"Candidate {workflow} contains an unsafe acceptance")
        if run.get("model") != _EXPECTED_MODEL:
            raise ValueError(f"Candidate {workflow} contains a model identity mismatch")


def _render_official_markdown(
    candidate_markdown: str,
    *,
    workflow: str,
    candidate_hash: str,
    manifest: Mapping[str, Any],
) -> str:
    """Convert the reviewed candidate report into an explicit official baseline report."""
    marker = "## Baseline candidate status"
    if marker not in candidate_markdown:
        raise ValueError(f"Candidate markdown for {workflow} lacks the status section")

    head, _separator, _tail = candidate_markdown.partition(marker)
    head = head.replace(
        "Adversarial Security Evaluation v2 Baseline Candidate",
        "Adversarial Security Evaluation v2 Baseline",
        1,
    ).rstrip()
    review_record = cast(str, manifest["review_record"])
    reviewed_at = cast(str, manifest["reviewed_at_utc"])
    reviewed_commit = cast(str, manifest["reviewed_against_repository_commit"])
    acceptance = (
        "\n\n## Baseline acceptance status\n\n"
        "This artifact is an **official adversarial v2 baseline** after manual review "
        "of every persisted attempt trace.\n\n"
        f"- Reviewed at: `{reviewed_at}`\n"
        f"- Reviewed against repository commit: `{reviewed_commit}`\n"
        f"- Source candidate SHA-256: `{candidate_hash}`\n"
        f"- Review record: [`{review_record}`](../../../{review_record})\n\n"
        "Acceptance is limited to this six-scenario evidence-plane suite and must not "
        "be interpreted as proof of general prompt-injection resistance.\n"
    )
    return head + acceptance


def promote_workflow(
    *,
    workflow: str,
    manifest: Mapping[str, Any],
    candidate_root: Path = _CANDIDATE_ROOT,
    baseline_root: Path = _BASELINE_ROOT,
) -> tuple[Path, Path]:
    """Promote one exact hash-approved candidate and preserve its original evidence."""
    candidate_dir = candidate_root / workflow
    candidate_json_path = candidate_dir / "latest.json"
    candidate_markdown_path = candidate_dir / "latest.md"
    if not candidate_json_path.is_file() or not candidate_markdown_path.is_file():
        raise FileNotFoundError(f"Missing candidate artifacts for {workflow}")

    candidate = load_json_object(candidate_json_path)
    validate_candidate(
        workflow=workflow,
        candidate_path=candidate_json_path,
        candidate=candidate,
        manifest=manifest,
    )
    candidate_hash = sha256_file(candidate_json_path)

    official = deepcopy(candidate)
    official["artifact_type"] = "baseline"
    official["official_baseline"] = True
    official["review_status"] = "accepted_manual_trace_review"
    official["reviewed_at_utc"] = manifest["reviewed_at_utc"]
    official["promotion"] = {
        "source_candidate_sha256": candidate_hash,
        "source_candidate_path": str(candidate_json_path),
        "review_record": manifest["review_record"],
        "reviewed_against_repository_commit": manifest[
            "reviewed_against_repository_commit"
        ],
        "scenario_fixture_blob_sha": manifest["scenario_fixture_blob_sha"],
        "adversarial_evaluator_blob_sha": manifest["adversarial_evaluator_blob_sha"],
    }

    baseline_dir = baseline_root / workflow
    baseline_dir.mkdir(parents=True, exist_ok=True)
    official_json_path = baseline_dir / "latest.json"
    official_markdown_path = baseline_dir / "latest.md"
    official_json_path.write_text(json.dumps(official, indent=2) + "\n")
    official_markdown_path.write_text(
        _render_official_markdown(
            candidate_markdown_path.read_text(),
            workflow=workflow,
            candidate_hash=candidate_hash,
            manifest=manifest,
        )
    )
    return official_json_path, official_markdown_path


def parse_workflows(
    argv: Sequence[str] | None = None,
) -> tuple[str, ...]:
    """Parse an optional subset while defaulting to every approved workflow."""
    parser = argparse.ArgumentParser(
        description="Promote manually reviewed adversarial v2 workflow baselines."
    )
    parser.add_argument(
        "--framework",
        action="append",
        dest="workflows",
        help="Workflow key to promote. Repeat to select multiple; omit to promote all approved.",
    )
    args = parser.parse_args(argv)
    selected = cast(list[str] | None, args.workflows)
    if not selected:
        return ()
    return tuple(dict.fromkeys(selected))


def main() -> None:
    """Promote exact candidates named by the accepted manual-review manifest."""
    manifest = load_review_manifest()
    selected = parse_workflows()
    candidates = manifest.get("candidates")
    if not isinstance(candidates, dict):
        raise ValueError("Review manifest candidates must be an object")
    workflows = selected or tuple(candidates)

    for workflow in workflows:
        json_path, markdown_path = promote_workflow(
            workflow=workflow,
            manifest=manifest,
        )
        print(f"promoted_json: {json_path}")
        print(f"promoted_markdown: {markdown_path}")


if __name__ == "__main__":
    main()
