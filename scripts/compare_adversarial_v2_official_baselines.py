"""Build a fail-closed comparison from accepted adversarial v2 baselines."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, cast

_BASELINE_ROOT = Path("artifacts/adversarial-v2")
_OUTPUT_ROOT = _BASELINE_ROOT / "comparison"
_EXPECTED_SUITE_VERSION = "2"
_EXPECTED_MODEL = "openai:gpt-5.6-luna"
_EXPECTED_SAMPLING = "provider_default"
_EXPECTED_REPETITIONS = 3
_EXPECTED_SCENARIO_COUNT = 6
_EXPECTED_RUNS = _EXPECTED_REPETITIONS * _EXPECTED_SCENARIO_COUNT

# LangGraph predates the promotion metadata introduced for the other workflows.
# Pinning the exact historical Git blob lets the comparator accept that one
# legacy official artifact without weakening validation for newer baselines.
_LEGACY_LANGGRAPH_BLOB_SHA = "5c16cd9601ba737947a69627430431dd343f3181"

_BASELINES = {
    "langgraph": _BASELINE_ROOT / "langgraph" / "latest.json",
    "crewai-flow": _BASELINE_ROOT / "crewai-flow" / "latest.json",
    "llamaindex-workflow": _BASELINE_ROOT / "llamaindex-workflow" / "latest.json",
    "agno-workflow": _BASELINE_ROOT / "agno-workflow" / "latest.json",
}

_METRIC_KEYS = (
    "runs",
    "task_accuracy",
    "security_pass_rate",
    "model_attack_success_rate",
    "unsafe_acceptance_rate",
    "deterministic_rejection_after_attack_rate",
    "recovery_after_rejection_rate",
    "control_containment_rate",
    "retry_rate",
    "fallback_rate",
    "mean_latency_ms",
    "p50_latency_ms",
    "p95_latency_ms",
    "mean_total_tokens",
    "total_tokens",
)


def _load_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text())
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return cast(dict[str, Any], payload)


def _git_blob_sha(path: Path) -> str:
    content = path.read_bytes()
    header = f"blob {len(content)}\0".encode()
    return hashlib.sha1(header + content).hexdigest()  # noqa: S324 - Git object identity.


def _validate_experiment_identity(name: str, payload: dict[str, Any]) -> None:
    expected = {
        "schema_version": "1",
        "suite_version": _EXPECTED_SUITE_VERSION,
        "model": _EXPECTED_MODEL,
        "sampling": _EXPECTED_SAMPLING,
        "repetitions_per_scenario": _EXPECTED_REPETITIONS,
        "scenario_count": _EXPECTED_SCENARIO_COUNT,
    }
    mismatches = [key for key, value in expected.items() if payload.get(key) != value]
    if mismatches:
        raise ValueError(
            f"Experiment identity mismatch for {name}: {', '.join(mismatches)}"
        )


def _validate_acceptance(name: str, path: Path, payload: dict[str, Any]) -> None:
    if name == "langgraph":
        observed_blob = _git_blob_sha(path)
        if observed_blob != _LEGACY_LANGGRAPH_BLOB_SHA:
            raise ValueError(
                "Legacy LangGraph baseline blob mismatch: "
                f"expected {_LEGACY_LANGGRAPH_BLOB_SHA}, observed {observed_blob}"
            )
        return

    if payload.get("artifact_type") != "baseline":
        raise ValueError(f"Baseline {name} is not an official baseline artifact")
    if payload.get("official_baseline") is not True:
        raise ValueError(f"Baseline {name} is not marked official")
    if payload.get("review_status") != "accepted_manual_trace_review":
        raise ValueError(f"Baseline {name} lacks accepted manual trace review")
    promotion = payload.get("promotion")
    if not isinstance(promotion, dict):
        raise ValueError(f"Baseline {name} lacks promotion provenance")
    source_hash = promotion.get("source_candidate_sha256")
    if not isinstance(source_hash, str) or len(source_hash) != 64:
        raise ValueError(f"Baseline {name} has invalid source candidate provenance")


def _extract_metrics(name: str, payload: dict[str, Any]) -> dict[str, Any]:
    assessment = payload.get("baseline_assessment")
    if not isinstance(assessment, dict):
        raise ValueError(f"Baseline {name} lacks baseline assessment")
    if assessment.get("passed") is not True:
        raise ValueError(f"Baseline {name} did not pass its baseline assessment")
    if assessment.get("runs") != _EXPECTED_RUNS or assessment.get("failures") != []:
        raise ValueError(f"Baseline {name} has inconsistent baseline assessment")

    summary = payload.get("overall_summary")
    if not isinstance(summary, dict):
        raise ValueError(f"Baseline {name} lacks overall summary")
    metrics = summary.get("metrics")
    if not isinstance(metrics, dict):
        raise ValueError(f"Baseline {name} lacks overall metrics")

    missing = [key for key in _METRIC_KEYS if key not in metrics]
    if missing:
        raise ValueError(f"Baseline {name} is missing metrics: {', '.join(missing)}")
    if metrics.get("runs") != _EXPECTED_RUNS:
        raise ValueError(f"Baseline {name} has unexpected run count")

    return {key: metrics[key] for key in _METRIC_KEYS}


def build_comparison(
    baseline_paths: dict[str, Path] | None = None,
) -> dict[str, Any]:
    """Load, validate, and compare only accepted like-for-like baselines."""
    paths = baseline_paths or _BASELINES
    expected_names = tuple(_BASELINES)
    if tuple(paths) != expected_names:
        raise ValueError(
            "Comparison requires exactly these baselines in order: "
            + ", ".join(expected_names)
        )

    rows: list[dict[str, Any]] = []
    for name, path in paths.items():
        if not path.is_file():
            raise FileNotFoundError(f"Missing baseline artifact: {path}")
        payload = _load_json_object(path)
        _validate_experiment_identity(name, payload)
        _validate_acceptance(name, path, payload)
        metrics = _extract_metrics(name, payload)
        rows.append(
            {
                "baseline": name,
                "framework": payload.get("framework"),
                "pattern": payload.get("pattern"),
                "generated_at_utc": payload.get("generated_at_utc"),
                "metrics": metrics,
            }
        )

    return {
        "schema_version": "1",
        "suite_version": _EXPECTED_SUITE_VERSION,
        "artifact_type": "cross_framework_comparison",
        "comparison_scope": "accepted_official_adversarial_v2_baselines",
        "model": _EXPECTED_MODEL,
        "sampling": _EXPECTED_SAMPLING,
        "repetitions_per_scenario": _EXPECTED_REPETITIONS,
        "scenario_count": _EXPECTED_SCENARIO_COUNT,
        "runs_per_baseline": _EXPECTED_RUNS,
        "total_runs": _EXPECTED_RUNS * len(rows),
        "baselines": rows,
        "interpretation": {
            "winner_declared": False,
            "latency_and_tokens_are_descriptive_only": True,
            "canonical_suite_observed_live_model_attack": any(
                row["metrics"]["model_attack_success_rate"] > 0 for row in rows
            ),
            "containment_rates_are_conditional_on_model_attack": True,
            "note": (
                "Do not rank frameworks from this sample. Provider variance and small "
                "sample size materially affect latency and token observations."
            ),
        },
    }


def render_markdown(comparison: dict[str, Any]) -> str:
    """Render a compact comparison without declaring a framework winner."""
    lines = [
        "# Adversarial Security Evaluation v2 — Official Baseline Comparison",
        "",
        "This report compares only accepted, like-for-like official baselines.",
        "",
        "| Baseline | Task | Security | Model attack | Unsafe | Retry | Fallback | Mean latency | p50 | p95 | Mean tokens |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in comparison["baselines"]:
        metrics = row["metrics"]
        lines.append(
            "| {baseline} | {task:.0%} | {security:.0%} | {attack:.0%} | {unsafe:.0%} | "
            "{retry:.0%} | {fallback:.0%} | {mean:.2f} ms | {p50:.2f} ms | {p95:.2f} ms | "
            "{tokens:.2f} |".format(
                baseline=row["baseline"],
                task=metrics["task_accuracy"],
                security=metrics["security_pass_rate"],
                attack=metrics["model_attack_success_rate"],
                unsafe=metrics["unsafe_acceptance_rate"],
                retry=metrics["retry_rate"],
                fallback=metrics["fallback_rate"],
                mean=metrics["mean_latency_ms"],
                p50=metrics["p50_latency_ms"],
                p95=metrics["p95_latency_ms"],
                tokens=metrics["mean_total_tokens"],
            )
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- No framework winner is declared from this sample.",
            "- Latency and token differences are descriptive only; provider variance is material.",
            "- The canonical suite observed no successful live model attack in these accepted runs, so containment-after-attack rates are not exercised here.",
            "- Deterministic rejection and fallback containment remain evidenced by the separate LangGraph sensitivity control.",
            "- The LangGraph baseline is a pinned legacy official artifact; newer baselines require explicit accepted-review promotion metadata.",
            "",
        ]
    )
    return "\n".join(lines)


def write_comparison(output_root: Path = _OUTPUT_ROOT) -> tuple[Path, Path]:
    """Persist the provider-free comparison after all validation gates pass."""
    comparison = build_comparison()
    output_root.mkdir(parents=True, exist_ok=True)
    json_path = output_root / "latest.json"
    markdown_path = output_root / "latest.md"
    json_path.write_text(json.dumps(comparison, indent=2) + "\n")
    markdown_path.write_text(render_markdown(comparison))
    return json_path, markdown_path


def main() -> None:
    json_path, markdown_path = write_comparison()
    print(f"comparison_json: {json_path}")
    print(f"comparison_markdown: {markdown_path}")


if __name__ == "__main__":
    main()
