"""Provider-free tests for adversarial v2 official baseline comparison."""

import json
from pathlib import Path
from runpy import run_path
from typing import Any

import pytest

_REPO_ROOT = Path(__file__).parents[2]
_SCRIPT = run_path(
    str(_REPO_ROOT / "scripts" / "compare_adversarial_v2_official_baselines.py")
)
build_comparison: Any = _SCRIPT["build_comparison"]
render_markdown: Any = _SCRIPT["render_markdown"]

_NAMES = (
    "langgraph",
    "crewai-flow",
    "llamaindex-workflow",
    "agno-workflow",
)


def _repo_paths() -> dict[str, Path]:
    return {
        name: _REPO_ROOT / "artifacts" / "adversarial-v2" / name / "latest.json"
        for name in _NAMES
    }


def _copy_baselines(tmp_path: Path) -> dict[str, Path]:
    copied: dict[str, Path] = {}
    for name, source in _repo_paths().items():
        target = tmp_path / name / "latest.json"
        target.parent.mkdir(parents=True)
        target.write_bytes(source.read_bytes())
        copied[name] = target
    return copied


def test_build_comparison_accepts_exact_official_evidence_set() -> None:
    comparison = build_comparison()

    assert comparison["total_runs"] == 72
    assert [row["baseline"] for row in comparison["baselines"]] == list(_NAMES)
    assert comparison["interpretation"]["winner_declared"] is False
    assert (
        comparison["interpretation"]["canonical_suite_observed_live_model_attack"]
        is False
    )
    for row in comparison["baselines"]:
        metrics = row["metrics"]
        assert metrics["runs"] == 18
        assert metrics["task_accuracy"] == 1.0
        assert metrics["security_pass_rate"] == 1.0
        assert metrics["model_attack_success_rate"] == 0.0
        assert metrics["unsafe_acceptance_rate"] == 0.0


def test_build_comparison_rejects_experiment_identity_mismatch(tmp_path: Path) -> None:
    paths = _copy_baselines(tmp_path)
    payload = json.loads(paths["crewai-flow"].read_text())
    payload["suite_version"] = "999"
    paths["crewai-flow"].write_text(json.dumps(payload, indent=2) + "\n")

    with pytest.raises(ValueError, match="Experiment identity mismatch"):
        build_comparison(paths)


def test_build_comparison_rejects_unofficial_modern_baseline(tmp_path: Path) -> None:
    paths = _copy_baselines(tmp_path)
    payload = json.loads(paths["agno-workflow"].read_text())
    payload["official_baseline"] = False
    paths["agno-workflow"].write_text(json.dumps(payload, indent=2) + "\n")

    with pytest.raises(ValueError, match="not marked official"):
        build_comparison(paths)


def test_build_comparison_rejects_modified_legacy_langgraph_blob(tmp_path: Path) -> None:
    paths = _copy_baselines(tmp_path)
    paths["langgraph"].write_bytes(paths["langgraph"].read_bytes() + b"\n")

    with pytest.raises(ValueError, match="Legacy LangGraph baseline blob mismatch"):
        build_comparison(paths)


def test_build_comparison_rejects_missing_metric(tmp_path: Path) -> None:
    paths = _copy_baselines(tmp_path)
    payload = json.loads(paths["llamaindex-workflow"].read_text())
    del payload["overall_summary"]["metrics"]["p95_latency_ms"]
    paths["llamaindex-workflow"].write_text(json.dumps(payload, indent=2) + "\n")

    with pytest.raises(ValueError, match="missing metrics"):
        build_comparison(paths)


def test_render_markdown_keeps_interpretation_descriptive() -> None:
    markdown = render_markdown(build_comparison())

    assert "No framework winner is declared" in markdown
    assert "descriptive only" in markdown
    assert "10" not in markdown or "winner" in markdown.lower()
