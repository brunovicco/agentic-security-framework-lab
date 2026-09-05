"""Tests for immutable final-evaluation artifact validation and persistence."""

import json
from pathlib import Path
from typing import cast

import pytest

from agentic_lab.entrypoints.final_evaluation import (
    FINAL_EVALUATION_BENCHMARK_JSON_PATHS,
    FINAL_EVALUATION_COMPARISON_JSON_PATH,
    FINAL_EVALUATION_MODEL_ALIAS,
    FINAL_EVALUATION_REPETITIONS,
    persist_final_evaluation_bundle,
    validate_final_benchmark_workspace,
    validate_final_evaluation_run_id,
)

_GIT_COMMIT = "a" * 40


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n")


def _write_workspace(
    root: Path,
    *,
    model_alias: str = FINAL_EVALUATION_MODEL_ALIAS,
    repetitions: int = FINAL_EVALUATION_REPETITIONS,
) -> None:
    for relative_path in FINAL_EVALUATION_BENCHMARK_JSON_PATHS:
        _write_json(
            root / relative_path,
            {
                "model": model_alias,
                "repetitions_per_scenario": repetitions,
                "overall_summary": {"model": model_alias},
            },
        )

    _write_json(
        root / FINAL_EVALUATION_COMPARISON_JSON_PATH,
        {
            "methodology": {
                "model": model_alias,
                "repetitions_per_scenario": repetitions,
            }
        },
    )
    (root / "comparison" / "five-way-latest.md").write_text("# Final comparison\n")


def _read_json(path: Path) -> dict[str, object]:
    payload: object = json.loads(path.read_text())
    assert isinstance(payload, dict)
    return cast(dict[str, object], payload)


def test_validate_final_workspace_accepts_governed_comparable_artifacts(tmp_path: Path) -> None:
    _write_workspace(tmp_path)

    validated = validate_final_benchmark_workspace(tmp_path)

    assert validated == (
        "langgraph/latest.json",
        "crewai/latest.json",
        "crewai-flow/latest.json",
        "llamaindex-workflow/latest.json",
        "agno-workflow/latest.json",
        "comparison/five-way-latest.json",
    )


def test_validate_final_workspace_rejects_provider_native_model(tmp_path: Path) -> None:
    _write_workspace(tmp_path)
    _write_json(
        tmp_path / "crewai/latest.json",
        {
            "model": "openai:gpt-5.6-luna",
            "repetitions_per_scenario": FINAL_EVALUATION_REPETITIONS,
            "overall_summary": {"model": "openai:gpt-5.6-luna"},
        },
    )

    with pytest.raises(RuntimeError, match="expected governed alias"):
        validate_final_benchmark_workspace(tmp_path)


def test_validate_final_workspace_rejects_wrong_repetition_count(tmp_path: Path) -> None:
    _write_workspace(tmp_path, repetitions=2)

    with pytest.raises(RuntimeError, match="expected 3"):
        validate_final_benchmark_workspace(tmp_path)


def test_persist_final_bundle_copies_evidence_and_records_provenance(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    destination_root = tmp_path / "final-evaluation"
    _write_workspace(workspace)

    destination = persist_final_evaluation_bundle(
        benchmark_root=workspace,
        destination_root=destination_root,
        run_id="20260905T123000Z",
        git_commit=_GIT_COMMIT,
    )

    assert destination == destination_root / "20260905T123000Z"
    assert (destination / "benchmarks" / "comparison" / "five-way-latest.md").read_text() == (
        "# Final comparison\n"
    )
    assert (workspace / "comparison" / "five-way-latest.md").is_file()

    manifest = _read_json(destination / "manifest.json")
    assert manifest["git_commit"] == _GIT_COMMIT
    assert manifest["model_alias"] == FINAL_EVALUATION_MODEL_ALIAS
    assert manifest["repetitions_per_scenario"] == FINAL_EVALUATION_REPETITIONS


def test_persist_final_bundle_never_overwrites_existing_run(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    destination_root = tmp_path / "final-evaluation"
    _write_workspace(workspace)
    (destination_root / "existing-run").mkdir(parents=True)

    with pytest.raises(FileExistsError, match="already exists"):
        persist_final_evaluation_bundle(
            benchmark_root=workspace,
            destination_root=destination_root,
            run_id="existing-run",
            git_commit=_GIT_COMMIT,
        )


def test_run_id_rejects_path_traversal() -> None:
    with pytest.raises(ValueError, match="must not contain"):
        validate_final_evaluation_run_id("../escape")
