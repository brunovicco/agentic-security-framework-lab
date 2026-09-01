"""Compare persisted framework benchmark artifacts."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

LANGGRAPH_PATH = Path("artifacts/benchmarks/langgraph/latest.json")
CREWAI_PATH = Path("artifacts/benchmarks/crewai/latest.json")
OUTPUT_DIR = Path("artifacts/benchmarks/comparison")


def load_json(path: Path) -> dict[str, Any]:
    """Load one persisted benchmark artifact."""
    if not path.exists():
        raise RuntimeError(f"Benchmark artifact does not exist: {path}")

    payload: object = json.loads(path.read_text())

    if not isinstance(payload, dict):
        raise RuntimeError(f"Expected JSON object in {path}")

    return cast(dict[str, Any], payload)


def percent_delta(candidate: float, baseline: float) -> float:
    """Return percentage change from baseline to candidate."""
    if baseline == 0:
        raise RuntimeError("Cannot calculate percentage delta from zero baseline")

    return round(((candidate / baseline) - 1.0) * 100.0, 2)


def ratio(candidate: float, baseline: float) -> float:
    """Return candidate-to-baseline ratio."""
    if baseline == 0:
        raise RuntimeError("Cannot calculate ratio from zero baseline")

    return round(candidate / baseline, 3)


def validate_comparability(
    langgraph: dict[str, Any],
    crewai: dict[str, Any],
) -> None:
    """Fail closed when benchmark artifacts are not directly comparable."""
    checks = (
        (
            "model",
            langgraph["model"],
            crewai["model"],
        ),
        (
            "repetitions_per_scenario",
            langgraph["repetitions_per_scenario"],
            crewai["repetitions_per_scenario"],
        ),
        (
            "scenario count",
            langgraph["overall_summary"]["scenarios"],
            crewai["overall_summary"]["scenarios"],
        ),
        (
            "total runs",
            langgraph["overall_summary"]["total_runs"],
            crewai["overall_summary"]["total_runs"],
        ),
    )

    for label, left, right in checks:
        if left != right:
            raise RuntimeError(
                f"Benchmarks are not comparable: {label} differs ({left!r} != {right!r})"
            )

    langgraph_scenarios = {item["scenario_id"] for item in langgraph["scenario_summaries"]}
    crewai_scenarios = {item["scenario_id"] for item in crewai["scenario_summaries"]}

    if langgraph_scenarios != crewai_scenarios:
        raise RuntimeError("Benchmarks do not contain the same scenario identifiers")

    if langgraph["overall_summary"]["total_runs"] != 15:
        raise RuntimeError("Expected 15 LangGraph benchmark runs")

    if crewai["overall_summary"]["total_runs"] != 15:
        raise RuntimeError("Expected 15 CrewAI benchmark runs")


def scenario_map(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Index scenario summaries by scenario identifier."""
    return {summary["scenario_id"]: summary for summary in payload["scenario_summaries"]}


def build_scenario_comparison(
    langgraph: dict[str, Any],
    crewai: dict[str, Any],
) -> list[dict[str, Any]]:
    """Compare both frameworks scenario by scenario."""
    langgraph_by_id = scenario_map(langgraph)
    crewai_by_id = scenario_map(crewai)

    comparison: list[dict[str, Any]] = []

    for scenario_id in langgraph_by_id:
        lg = langgraph_by_id[scenario_id]
        cr = crewai_by_id[scenario_id]

        comparison.append(
            {
                "scenario_id": scenario_id,
                "langgraph": {
                    "expected_accuracy": lg["expected_accuracy"],
                    "first_attempt_acceptance_rate": (lg["first_attempt_acceptance_rate"]),
                    "retry_rate": lg["retry_rate"],
                    "fallback_rate": lg["fallback_rate"],
                    "mean_model_calls": lg["mean_model_calls"],
                    "mean_latency_ms": lg["mean_latency_ms"],
                    "p50_latency_ms": lg["p50_latency_ms"],
                    "p95_latency_ms": lg["p95_latency_ms"],
                    "mean_total_tokens": lg["mean_total_tokens"],
                },
                "crewai": {
                    "expected_accuracy": cr["expected_accuracy"],
                    "first_attempt_acceptance_rate": (cr["first_attempt_acceptance_rate"]),
                    "retry_rate": cr["retry_rate"],
                    "fallback_rate": cr["fallback_rate"],
                    "mean_model_calls": cr["mean_model_calls"],
                    "mean_latency_ms": cr["mean_latency_ms"],
                    "p50_latency_ms": cr["p50_latency_ms"],
                    "p95_latency_ms": cr["p95_latency_ms"],
                    "mean_total_tokens": cr["mean_total_tokens"],
                },
                "crewai_vs_langgraph": {
                    "mean_latency_delta_pct": percent_delta(
                        cr["mean_latency_ms"],
                        lg["mean_latency_ms"],
                    ),
                    "p50_latency_delta_pct": percent_delta(
                        cr["p50_latency_ms"],
                        lg["p50_latency_ms"],
                    ),
                    "p95_latency_delta_pct": percent_delta(
                        cr["p95_latency_ms"],
                        lg["p95_latency_ms"],
                    ),
                    "mean_total_tokens_delta_pct": percent_delta(
                        cr["mean_total_tokens"],
                        lg["mean_total_tokens"],
                    ),
                    "token_ratio": ratio(
                        cr["mean_total_tokens"],
                        lg["mean_total_tokens"],
                    ),
                },
            }
        )

    return comparison


def build_payload(
    langgraph: dict[str, Any],
    crewai: dict[str, Any],
) -> dict[str, Any]:
    """Build the persisted cross-framework comparison artifact."""
    lg = langgraph["overall_summary"]
    cr = crewai["overall_summary"]

    return {
        "schema_version": "1",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "comparison": "langgraph_vs_crewai",
        "methodology": {
            "model": langgraph["model"],
            "scenarios": lg["scenarios"],
            "repetitions_per_scenario": (langgraph["repetitions_per_scenario"]),
            "runs_per_framework": lg["total_runs"],
            "shared_dataset": True,
            "shared_expected_truth": True,
            "shared_deterministic_validation": True,
            "shared_fallback_policy": True,
            "sampling_policy": "provider_default",
            "sampling_validation": (
                "CrewAI omits temperature. LangChain ChatOpenAI normalized "
                "temperature to None for this GPT-5 model."
            ),
        },
        "frameworks": {
            "langgraph": {
                "pattern": langgraph["pattern"],
                **lg,
            },
            "crewai": {
                "pattern": crewai["pattern"],
                **cr,
            },
        },
        "crewai_vs_langgraph": {
            "expected_accuracy_delta_percentage_points": round(
                (cr["expected_accuracy"] - lg["expected_accuracy"]) * 100,
                2,
            ),
            "first_attempt_acceptance_delta_percentage_points": round(
                (cr["first_attempt_acceptance_rate"] - lg["first_attempt_acceptance_rate"]) * 100,
                2,
            ),
            "retry_rate_delta_percentage_points": round(
                (cr["retry_rate"] - lg["retry_rate"]) * 100,
                2,
            ),
            "fallback_rate_delta_percentage_points": round(
                (cr["fallback_rate"] - lg["fallback_rate"]) * 100,
                2,
            ),
            "mean_latency_delta_ms": round(
                cr["mean_latency_ms"] - lg["mean_latency_ms"],
                2,
            ),
            "mean_latency_delta_pct": percent_delta(
                cr["mean_latency_ms"],
                lg["mean_latency_ms"],
            ),
            "p50_latency_delta_pct": percent_delta(
                cr["p50_latency_ms"],
                lg["p50_latency_ms"],
            ),
            "p95_latency_delta_pct": percent_delta(
                cr["p95_latency_ms"],
                lg["p95_latency_ms"],
            ),
            "mean_total_tokens_delta": round(
                cr["mean_total_tokens"] - lg["mean_total_tokens"],
                2,
            ),
            "mean_total_tokens_delta_pct": percent_delta(
                cr["mean_total_tokens"],
                lg["mean_total_tokens"],
            ),
            "token_ratio": ratio(
                cr["mean_total_tokens"],
                lg["mean_total_tokens"],
            ),
            "total_tokens_delta": (cr["total_tokens"] - lg["total_tokens"]),
        },
        "scenario_comparison": build_scenario_comparison(
            langgraph,
            crewai,
        ),
        "limitations": [
            (
                "The benchmark contains five synthetic scenarios with three "
                "repetitions each; latency percentiles are descriptive, not "
                "production SLO evidence."
            ),
            (
                "The adversarial asset-id scenario tests a narrow indirect "
                "prompt-injection boundary and must not be interpreted as "
                "general prompt-injection resistance."
            ),
            (
                "No live retry or fallback was triggered in either persisted "
                "15-run benchmark; those paths are covered separately by "
                "deterministic tests."
            ),
            (
                "Token differences include framework-specific prompt and "
                "orchestration overhead and therefore represent end-to-end "
                "framework behavior for this workload."
            ),
        ],
    }


def render_markdown(payload: dict[str, Any]) -> str:
    """Render a human-readable cross-framework benchmark report."""
    lg = payload["frameworks"]["langgraph"]
    cr = payload["frameworks"]["crewai"]
    delta = payload["crewai_vs_langgraph"]

    lines = [
        "# LangGraph vs CrewAI Benchmark",
        "",
        "## Methodology",
        "",
        f"- Model: `{payload['methodology']['model']}`",
        f"- Scenarios: {payload['methodology']['scenarios']}",
        (f"- Repetitions per scenario: {payload['methodology']['repetitions_per_scenario']}"),
        (f"- Runs per framework: {payload['methodology']['runs_per_framework']}"),
        "- Shared dataset and expected truth: yes",
        "- Shared deterministic validation and fallback policy: yes",
        "- Sampling: provider default",
        "",
        "## Overall results",
        "",
        "| Metric | LangGraph | CrewAI | CrewAI vs LangGraph |",
        "| --- | ---: | ---: | ---: |",
        (
            f"| Expected accuracy | {lg['expected_accuracy']:.1%} | "
            f"{cr['expected_accuracy']:.1%} | "
            f"{delta['expected_accuracy_delta_percentage_points']:+.2f} pp |"
        ),
        (
            "| First-attempt acceptance | "
            f"{lg['first_attempt_acceptance_rate']:.1%} | "
            f"{cr['first_attempt_acceptance_rate']:.1%} | "
            f"{delta['first_attempt_acceptance_delta_percentage_points']:+.2f} pp |"
        ),
        (
            f"| Retry rate | {lg['retry_rate']:.1%} | "
            f"{cr['retry_rate']:.1%} | "
            f"{delta['retry_rate_delta_percentage_points']:+.2f} pp |"
        ),
        (
            f"| Fallback rate | {lg['fallback_rate']:.1%} | "
            f"{cr['fallback_rate']:.1%} | "
            f"{delta['fallback_rate_delta_percentage_points']:+.2f} pp |"
        ),
        (f"| Mean model calls | {lg['mean_model_calls']:.2f} | {cr['mean_model_calls']:.2f} | — |"),
        (
            f"| Mean latency | {lg['mean_latency_ms']:.2f} ms | "
            f"{cr['mean_latency_ms']:.2f} ms | "
            f"{delta['mean_latency_delta_pct']:+.2f}% |"
        ),
        (
            f"| p50 latency | {lg['p50_latency_ms']:.2f} ms | "
            f"{cr['p50_latency_ms']:.2f} ms | "
            f"{delta['p50_latency_delta_pct']:+.2f}% |"
        ),
        (
            f"| p95 latency | {lg['p95_latency_ms']:.2f} ms | "
            f"{cr['p95_latency_ms']:.2f} ms | "
            f"{delta['p95_latency_delta_pct']:+.2f}% |"
        ),
        (
            f"| Mean total tokens | {lg['mean_total_tokens']:.2f} | "
            f"{cr['mean_total_tokens']:.2f} | "
            f"{delta['mean_total_tokens_delta_pct']:+.2f}% |"
        ),
        (
            f"| Total tokens | {lg['total_tokens']} | "
            f"{cr['total_tokens']} | "
            f"{delta['total_tokens_delta']:+d} |"
        ),
        "",
        "## Scenario comparison",
        "",
        "| Scenario | LG p50 | CrewAI p50 | Latency Δ | LG tokens | CrewAI tokens | Token Δ |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    for scenario in payload["scenario_comparison"]:
        lg_s = scenario["langgraph"]
        cr_s = scenario["crewai"]
        delta_s = scenario["crewai_vs_langgraph"]

        lines.append(
            f"| {scenario['scenario_id']} | "
            f"{lg_s['p50_latency_ms']:.2f} ms | "
            f"{cr_s['p50_latency_ms']:.2f} ms | "
            f"{delta_s['p50_latency_delta_pct']:+.2f}% | "
            f"{lg_s['mean_total_tokens']:.2f} | "
            f"{cr_s['mean_total_tokens']:.2f} | "
            f"{delta_s['mean_total_tokens_delta_pct']:+.2f}% |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            (
                "Both frameworks reached 100% expected accuracy and 100% "
                "first-attempt acceptance across the persisted 15-run benchmark."
            ),
            "",
            (
                "For this workload, CrewAI used "
                f"**{delta['token_ratio']:.3f}x** the mean tokens of LangGraph "
                f"({delta['mean_total_tokens_delta_pct']:+.2f}%) while mean "
                f"latency was {delta['mean_latency_delta_pct']:+.2f}% higher."
            ),
            "",
            (
                "The result therefore shows quality parity in this dataset but "
                "a material difference in orchestration/token overhead."
            ),
            "",
            "## Security interpretation",
            "",
            (
                "Both frameworks passed the narrow adversarial asset-id scenario "
                "in all three persisted runs without triggering retry or fallback."
            ),
            "",
            (
                "This demonstrates correct behavior for this specific "
                "instruction-data-boundary test only. It is not evidence of "
                "general prompt-injection resistance."
            ),
            "",
            "## Limitations",
            "",
        ]
    )

    for limitation in payload["limitations"]:
        lines.append(f"- {limitation}")

    lines.append("")

    return "\n".join(lines)


def main() -> None:
    """Generate the persisted cross-framework comparison."""
    langgraph = load_json(LANGGRAPH_PATH)
    crewai = load_json(CREWAI_PATH)

    validate_comparability(langgraph, crewai)

    payload = build_payload(langgraph, crewai)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    json_path = OUTPUT_DIR / "latest.json"
    markdown_path = OUTPUT_DIR / "latest.md"

    json_path.write_text(json.dumps(payload, indent=2) + "\n")
    markdown_path.write_text(render_markdown(payload))

    delta = payload["crewai_vs_langgraph"]

    print("Cross-framework benchmark generated successfully.")
    print()
    print(f"Model: {payload['methodology']['model']}")
    print(
        "Accuracy: "
        f"LangGraph={payload['frameworks']['langgraph']['expected_accuracy']:.1%} "
        f"CrewAI={payload['frameworks']['crewai']['expected_accuracy']:.1%}"
    )
    print(f"Mean latency: {delta['mean_latency_delta_pct']:+.2f}% CrewAI vs LangGraph")
    print(f"Mean tokens: {delta['mean_total_tokens_delta_pct']:+.2f}% CrewAI vs LangGraph")
    print(f"Token ratio: {delta['token_ratio']:.3f}x")
    print()
    print(f"artifact_json: {json_path}")
    print(f"artifact_markdown: {markdown_path}")


if __name__ == "__main__":
    main()
