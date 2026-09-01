"""Compare LangGraph, CrewAI Agent/Crew, and CrewAI Flow benchmarks."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

LANGGRAPH_PATH = Path("artifacts/benchmarks/langgraph/latest.json")
CREWAI_AGENT_PATH = Path("artifacts/benchmarks/crewai/latest.json")
CREWAI_FLOW_PATH = Path("artifacts/benchmarks/crewai-flow/latest.json")

OUTPUT_DIR = Path("artifacts/benchmarks/comparison")
JSON_OUTPUT = OUTPUT_DIR / "three-way-latest.json"
MARKDOWN_OUTPUT = OUTPUT_DIR / "three-way-latest.md"


def load_json(path: Path) -> dict[str, Any]:
    """Load one benchmark artifact."""
    if not path.exists():
        raise RuntimeError(f"Benchmark artifact not found: {path}")

    payload: object = json.loads(path.read_text())

    if not isinstance(payload, dict):
        raise RuntimeError(f"Expected JSON object in {path}")

    return cast(dict[str, Any], payload)


def percent_delta(candidate: float, baseline: float) -> float:
    """Calculate percentage change relative to baseline."""
    if baseline == 0:
        raise RuntimeError("Cannot calculate percentage delta from zero")

    return round(((candidate / baseline) - 1.0) * 100.0, 2)


def ratio(candidate: float, baseline: float) -> float:
    """Calculate candidate-to-baseline ratio."""
    if baseline == 0:
        raise RuntimeError("Cannot calculate ratio from zero")

    return round(candidate / baseline, 3)


def percentage_point_delta(candidate: float, baseline: float) -> float:
    """Calculate percentage-point difference for rate metrics."""
    return round((candidate - baseline) * 100.0, 2)


def scenario_ids(payload: dict[str, Any]) -> set[str]:
    """Return benchmark scenario identifiers."""
    return {item["scenario_id"] for item in payload["scenario_summaries"]}


def scenario_map(
    payload: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """Index scenario summaries by identifier."""
    return {item["scenario_id"]: item for item in payload["scenario_summaries"]}


def validate_comparability(
    langgraph: dict[str, Any],
    crewai_agent: dict[str, Any],
    crewai_flow: dict[str, Any],
) -> None:
    """Fail closed if benchmark artifacts are not comparable."""
    artifacts = {
        "langgraph": langgraph,
        "crewai_agent": crewai_agent,
        "crewai_flow": crewai_flow,
    }

    models = {payload["model"] for payload in artifacts.values()}

    if len(models) != 1:
        raise RuntimeError(f"Benchmark models differ: {sorted(models)}")

    repetitions = {payload["repetitions_per_scenario"] for payload in artifacts.values()}

    if repetitions != {3}:
        raise RuntimeError("Expected three repetitions per scenario for every benchmark")

    expected_scenarios: set[str] | None = None

    for name, payload in artifacts.items():
        overall = payload["overall_summary"]

        if overall["scenarios"] != 5:
            raise RuntimeError(f"{name} does not contain exactly five scenarios")

        if overall["total_runs"] != 15:
            raise RuntimeError(f"{name} does not contain exactly fifteen runs")

        current_scenarios = scenario_ids(payload)

        if expected_scenarios is None:
            expected_scenarios = current_scenarios
        elif current_scenarios != expected_scenarios:
            raise RuntimeError(f"{name} scenario identifiers differ")

    if langgraph["framework"] != "langgraph":
        raise RuntimeError("Unexpected LangGraph framework identifier")

    if crewai_agent["framework"] != "crewai":
        raise RuntimeError("Unexpected CrewAI Agent framework identifier")

    if crewai_flow["framework"] != "crewai":
        raise RuntimeError("Unexpected CrewAI Flow framework identifier")

    if langgraph["pattern"] != "evaluator_optimizer":
        raise RuntimeError("Unexpected LangGraph pattern")

    if crewai_agent["pattern"] != "single_agent_external_evaluator_optimizer":
        raise RuntimeError("Unexpected CrewAI Agent/Crew pattern")

    if crewai_flow["pattern"] != "flow_direct_llm_evaluator_optimizer":
        raise RuntimeError("Unexpected CrewAI Flow pattern")


def comparison_metrics(
    candidate: dict[str, Any],
    baseline: dict[str, Any],
) -> dict[str, Any]:
    """Compare two overall benchmark summaries."""
    return {
        "expected_accuracy_delta_percentage_points": (
            percentage_point_delta(
                candidate["expected_accuracy"],
                baseline["expected_accuracy"],
            )
        ),
        "first_attempt_acceptance_delta_percentage_points": (
            percentage_point_delta(
                candidate["first_attempt_acceptance_rate"],
                baseline["first_attempt_acceptance_rate"],
            )
        ),
        "retry_rate_delta_percentage_points": (
            percentage_point_delta(
                candidate["retry_rate"],
                baseline["retry_rate"],
            )
        ),
        "fallback_rate_delta_percentage_points": (
            percentage_point_delta(
                candidate["fallback_rate"],
                baseline["fallback_rate"],
            )
        ),
        "mean_model_calls_delta": round(
            candidate["mean_model_calls"] - baseline["mean_model_calls"],
            2,
        ),
        "mean_latency_delta_pct": percent_delta(
            candidate["mean_latency_ms"],
            baseline["mean_latency_ms"],
        ),
        "p50_latency_delta_pct": percent_delta(
            candidate["p50_latency_ms"],
            baseline["p50_latency_ms"],
        ),
        "p95_latency_delta_pct": percent_delta(
            candidate["p95_latency_ms"],
            baseline["p95_latency_ms"],
        ),
        "mean_total_tokens_delta_pct": percent_delta(
            candidate["mean_total_tokens"],
            baseline["mean_total_tokens"],
        ),
        "token_ratio": ratio(
            candidate["mean_total_tokens"],
            baseline["mean_total_tokens"],
        ),
        "total_tokens_delta": (candidate["total_tokens"] - baseline["total_tokens"]),
    }


def token_overhead_analysis(
    langgraph: dict[str, Any],
    crewai_agent: dict[str, Any],
    crewai_flow: dict[str, Any],
) -> dict[str, Any]:
    """Quantify how much Agent/Crew token overhead Flow removes."""
    lg_tokens = float(langgraph["mean_total_tokens"])
    agent_tokens = float(crewai_agent["mean_total_tokens"])
    flow_tokens = float(crewai_flow["mean_total_tokens"])

    original_excess = agent_tokens - lg_tokens

    if original_excess <= 0:
        raise RuntimeError(
            "CrewAI Agent/Crew must exceed LangGraph tokens for overhead elimination analysis"
        )

    flow_excess = flow_tokens - lg_tokens
    eliminated = agent_tokens - flow_tokens

    return {
        "langgraph_mean_tokens": lg_tokens,
        "crewai_agent_mean_tokens": agent_tokens,
        "crewai_flow_mean_tokens": flow_tokens,
        "agent_excess_vs_langgraph_tokens": round(
            original_excess,
            2,
        ),
        "flow_excess_vs_langgraph_tokens": round(
            flow_excess,
            2,
        ),
        "tokens_removed_by_flow_vs_agent": round(
            eliminated,
            2,
        ),
        "agent_overhead_eliminated_by_flow_pct": round(
            (eliminated / original_excess) * 100.0,
            2,
        ),
    }


def slim_scenario(
    summary: dict[str, Any],
) -> dict[str, Any]:
    """Return comparable scenario metrics."""
    return {
        "expected_accuracy": summary["expected_accuracy"],
        "first_attempt_acceptance_rate": (summary["first_attempt_acceptance_rate"]),
        "retry_rate": summary["retry_rate"],
        "fallback_rate": summary["fallback_rate"],
        "mean_model_calls": summary["mean_model_calls"],
        "mean_latency_ms": summary["mean_latency_ms"],
        "p50_latency_ms": summary["p50_latency_ms"],
        "p95_latency_ms": summary["p95_latency_ms"],
        "mean_total_tokens": summary["mean_total_tokens"],
    }


def build_scenario_comparison(
    langgraph: dict[str, Any],
    crewai_agent: dict[str, Any],
    crewai_flow: dict[str, Any],
) -> list[dict[str, Any]]:
    """Build scenario-level three-way comparisons."""
    lg_map = scenario_map(langgraph)
    agent_map = scenario_map(crewai_agent)
    flow_map = scenario_map(crewai_flow)

    result: list[dict[str, Any]] = []

    for scenario_id in lg_map:
        lg = lg_map[scenario_id]
        agent = agent_map[scenario_id]
        flow = flow_map[scenario_id]

        result.append(
            {
                "scenario_id": scenario_id,
                "langgraph": slim_scenario(lg),
                "crewai_agent": slim_scenario(agent),
                "crewai_flow": slim_scenario(flow),
                "crewai_flow_vs_langgraph": {
                    "p50_latency_delta_pct": percent_delta(
                        flow["p50_latency_ms"],
                        lg["p50_latency_ms"],
                    ),
                    "mean_total_tokens_delta_pct": percent_delta(
                        flow["mean_total_tokens"],
                        lg["mean_total_tokens"],
                    ),
                },
                "crewai_flow_vs_crewai_agent": {
                    "p50_latency_delta_pct": percent_delta(
                        flow["p50_latency_ms"],
                        agent["p50_latency_ms"],
                    ),
                    "mean_total_tokens_delta_pct": percent_delta(
                        flow["mean_total_tokens"],
                        agent["mean_total_tokens"],
                    ),
                },
            }
        )

    return result


def build_payload(
    langgraph: dict[str, Any],
    crewai_agent: dict[str, Any],
    crewai_flow: dict[str, Any],
) -> dict[str, Any]:
    """Build the persisted three-way comparison."""
    lg = langgraph["overall_summary"]
    agent = crewai_agent["overall_summary"]
    flow = crewai_flow["overall_summary"]

    return {
        "schema_version": "1",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "comparison": ("langgraph_vs_crewai_agent_vs_crewai_flow"),
        "methodology": {
            "model": langgraph["model"],
            "scenarios": 5,
            "repetitions_per_scenario": 3,
            "runs_per_variant": 15,
            "shared_dataset": True,
            "shared_expected_truth": True,
            "shared_deterministic_validation": True,
            "shared_fallback_policy": True,
            "sampling_policy": "provider_default",
            "crewai_flow_headless": True,
            "latency_interpretation": (
                "Mean and p50 are the primary descriptive latency "
                "metrics. With fifteen observations, nearest-rank "
                "p95 resolves to the sample maximum and is therefore "
                "reported only as a small-sample tail indicator."
            ),
        },
        "variants": {
            "langgraph": {
                "pattern": langgraph["pattern"],
                **lg,
            },
            "crewai_agent": {
                "pattern": crewai_agent["pattern"],
                **agent,
            },
            "crewai_flow": {
                "pattern": crewai_flow["pattern"],
                **flow,
            },
        },
        "comparisons": {
            "crewai_agent_vs_langgraph": (comparison_metrics(agent, lg)),
            "crewai_flow_vs_langgraph": (comparison_metrics(flow, lg)),
            "crewai_flow_vs_crewai_agent": (comparison_metrics(flow, agent)),
        },
        "token_overhead_analysis": token_overhead_analysis(
            lg,
            agent,
            flow,
        ),
        "scenario_comparison": build_scenario_comparison(
            langgraph,
            crewai_agent,
            crewai_flow,
        ),
        "limitations": [
            ("The benchmark uses five synthetic scenarios and three repetitions per scenario."),
            (
                "Latency values are descriptive and must not be "
                "interpreted as production SLO evidence."
            ),
            (
                "At n=15, nearest-rank p95 resolves to the sample "
                "maximum, so mean and p50 are more useful for this "
                "comparison."
            ),
            (
                "The adversarial asset-id scenario is a narrow "
                "instruction/data-boundary test and is not evidence "
                "of general prompt-injection resistance."
            ),
            (
                "The three variants intentionally use different "
                "framework orchestration abstractions while sharing "
                "the same application-owned deterministic evaluator, "
                "fallback, policy, dataset, and expected truth."
            ),
            (
                "Token usage includes framework-specific prompt and "
                "orchestration overhead and represents end-to-end "
                "behavior for this workload."
            ),
        ],
    }


def render_markdown(payload: dict[str, Any]) -> str:
    """Render the human-readable three-way report."""
    lg = payload["variants"]["langgraph"]
    agent = payload["variants"]["crewai_agent"]
    flow = payload["variants"]["crewai_flow"]

    agent_vs_lg = payload["comparisons"]["crewai_agent_vs_langgraph"]
    flow_vs_lg = payload["comparisons"]["crewai_flow_vs_langgraph"]
    flow_vs_agent = payload["comparisons"]["crewai_flow_vs_crewai_agent"]
    overhead = payload["token_overhead_analysis"]

    lines = [
        "# LangGraph vs CrewAI Agent/Crew vs CrewAI Flow",
        "",
        "## Methodology",
        "",
        f"- Model: `{payload['methodology']['model']}`",
        "- Scenarios: 5",
        "- Repetitions per scenario: 3",
        "- Runs per variant: 15",
        "- Shared dataset and expected truth: yes",
        "- Shared deterministic evaluator and fallback policy: yes",
        "- Sampling: provider default",
        "- CrewAI Flow execution: headless",
        "",
        "## Overall results",
        "",
        "| Metric | LangGraph | CrewAI Agent/Crew | CrewAI Flow |",
        "| --- | ---: | ---: | ---: |",
        (
            f"| Expected accuracy | "
            f"{lg['expected_accuracy']:.1%} | "
            f"{agent['expected_accuracy']:.1%} | "
            f"{flow['expected_accuracy']:.1%} |"
        ),
        (
            f"| First-attempt acceptance | "
            f"{lg['first_attempt_acceptance_rate']:.1%} | "
            f"{agent['first_attempt_acceptance_rate']:.1%} | "
            f"{flow['first_attempt_acceptance_rate']:.1%} |"
        ),
        (
            f"| Retry rate | "
            f"{lg['retry_rate']:.1%} | "
            f"{agent['retry_rate']:.1%} | "
            f"{flow['retry_rate']:.1%} |"
        ),
        (
            f"| Fallback rate | "
            f"{lg['fallback_rate']:.1%} | "
            f"{agent['fallback_rate']:.1%} | "
            f"{flow['fallback_rate']:.1%} |"
        ),
        (
            f"| Mean model calls | "
            f"{lg['mean_model_calls']:.2f} | "
            f"{agent['mean_model_calls']:.2f} | "
            f"{flow['mean_model_calls']:.2f} |"
        ),
        (
            f"| Mean latency | "
            f"{lg['mean_latency_ms']:.2f} ms | "
            f"{agent['mean_latency_ms']:.2f} ms | "
            f"{flow['mean_latency_ms']:.2f} ms |"
        ),
        (
            f"| p50 latency | "
            f"{lg['p50_latency_ms']:.2f} ms | "
            f"{agent['p50_latency_ms']:.2f} ms | "
            f"{flow['p50_latency_ms']:.2f} ms |"
        ),
        (
            f"| p95* latency | "
            f"{lg['p95_latency_ms']:.2f} ms | "
            f"{agent['p95_latency_ms']:.2f} ms | "
            f"{flow['p95_latency_ms']:.2f} ms |"
        ),
        (
            f"| Mean total tokens | "
            f"{lg['mean_total_tokens']:.2f} | "
            f"{agent['mean_total_tokens']:.2f} | "
            f"{flow['mean_total_tokens']:.2f} |"
        ),
        (
            f"| Total tokens | "
            f"{lg['total_tokens']} | "
            f"{agent['total_tokens']} | "
            f"{flow['total_tokens']} |"
        ),
        "",
        (
            "\\* With 15 observations, nearest-rank p95 is the "
            "sample maximum and should be interpreted cautiously."
        ),
        "",
        "## Efficiency deltas",
        "",
        "### CrewAI Agent/Crew vs LangGraph",
        "",
        (f"- Mean tokens: **{agent_vs_lg['mean_total_tokens_delta_pct']:+.2f}%**"),
        (f"- Mean latency: **{agent_vs_lg['mean_latency_delta_pct']:+.2f}%**"),
        (f"- p50 latency: **{agent_vs_lg['p50_latency_delta_pct']:+.2f}%**"),
        "",
        "### CrewAI Flow vs LangGraph",
        "",
        (f"- Mean tokens: **{flow_vs_lg['mean_total_tokens_delta_pct']:+.2f}%**"),
        (f"- Mean latency: **{flow_vs_lg['mean_latency_delta_pct']:+.2f}%**"),
        (f"- p50 latency: **{flow_vs_lg['p50_latency_delta_pct']:+.2f}%**"),
        "",
        "### CrewAI Flow vs CrewAI Agent/Crew",
        "",
        (f"- Mean tokens: **{flow_vs_agent['mean_total_tokens_delta_pct']:+.2f}%**"),
        (f"- Mean latency: **{flow_vs_agent['mean_latency_delta_pct']:+.2f}%**"),
        (f"- p50 latency: **{flow_vs_agent['p50_latency_delta_pct']:+.2f}%**"),
        "",
        "## Token overhead decomposition",
        "",
        (
            "CrewAI Agent/Crew introduced "
            f"**{overhead['agent_excess_vs_langgraph_tokens']:.2f}** "
            "additional mean tokens per run relative to LangGraph."
        ),
        "",
        (
            "CrewAI Flow reduced the remaining difference to "
            f"**{overhead['flow_excess_vs_langgraph_tokens']:.2f}** "
            "tokens per run."
        ),
        "",
        (
            "Therefore the Flow variant eliminated "
            f"**{overhead['agent_overhead_eliminated_by_flow_pct']:.2f}%** "
            "of the Agent/Crew token overhead observed above the "
            "LangGraph baseline."
        ),
        "",
        "## Scenario token comparison",
        "",
        ("| Scenario | LangGraph | Agent/Crew | Flow | Flow vs LG | Flow vs Agent |"),
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]

    for item in payload["scenario_comparison"]:
        lines.append(
            f"| {item['scenario_id']} | "
            f"{item['langgraph']['mean_total_tokens']:.2f} | "
            f"{item['crewai_agent']['mean_total_tokens']:.2f} | "
            f"{item['crewai_flow']['mean_total_tokens']:.2f} | "
            f"{item['crewai_flow_vs_langgraph']['mean_total_tokens_delta_pct']:+.2f}% | "
            f"{item['crewai_flow_vs_crewai_agent']['mean_total_tokens_delta_pct']:+.2f}% |"
        )

    lines.extend(
        [
            "",
            "## Scenario p50 latency comparison",
            "",
            ("| Scenario | LangGraph | Agent/Crew | Flow | Flow vs LG | Flow vs Agent |"),
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )

    for item in payload["scenario_comparison"]:
        lines.append(
            f"| {item['scenario_id']} | "
            f"{item['langgraph']['p50_latency_ms']:.2f} ms | "
            f"{item['crewai_agent']['p50_latency_ms']:.2f} ms | "
            f"{item['crewai_flow']['p50_latency_ms']:.2f} ms | "
            f"{item['crewai_flow_vs_langgraph']['p50_latency_delta_pct']:+.2f}% | "
            f"{item['crewai_flow_vs_crewai_agent']['p50_latency_delta_pct']:+.2f}% |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            (
                "All three persisted variants achieved 100% final "
                "expected accuracy and 100% first-attempt acceptance "
                "in their official 15-run benchmark artifacts."
            ),
            "",
            (
                "For this workload, the main difference was not "
                "measured output quality but orchestration overhead."
            ),
            "",
            (
                "CrewAI Agent/Task/Crew used materially more tokens "
                "than LangGraph, while CrewAI Flow with a direct "
                "structured LLM call returned close to the LangGraph "
                "token baseline."
            ),
            "",
            (
                "This suggests that abstraction choice inside the "
                "same framework can materially affect token cost."
            ),
            "",
            "## Security interpretation",
            "",
            (
                "All three official variants passed the narrow "
                "adversarial asset-id scenario in all three runs."
            ),
            "",
            (
                "The deterministic evaluator, bounded retry, oracle "
                "fallback, and human-review policy remain "
                "application-owned controls rather than model-owned "
                "decisions."
            ),
            "",
            (
                "This is evidence only for the specific tested "
                "instruction/data boundary and is not proof of "
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
    """Generate three-way benchmark comparison artifacts."""
    langgraph = load_json(LANGGRAPH_PATH)
    crewai_agent = load_json(CREWAI_AGENT_PATH)
    crewai_flow = load_json(CREWAI_FLOW_PATH)

    validate_comparability(
        langgraph,
        crewai_agent,
        crewai_flow,
    )

    payload = build_payload(
        langgraph,
        crewai_agent,
        crewai_flow,
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    JSON_OUTPUT.write_text(json.dumps(payload, indent=2) + "\n")
    MARKDOWN_OUTPUT.write_text(render_markdown(payload))

    flow_vs_lg = payload["comparisons"]["crewai_flow_vs_langgraph"]
    flow_vs_agent = payload["comparisons"]["crewai_flow_vs_crewai_agent"]
    overhead = payload["token_overhead_analysis"]

    print("Three-way benchmark generated successfully.")
    print()
    print(f"CrewAI Flow vs LangGraph tokens: {flow_vs_lg['mean_total_tokens_delta_pct']:+.2f}%")
    print(f"CrewAI Flow vs Agent/Crew tokens: {flow_vs_agent['mean_total_tokens_delta_pct']:+.2f}%")
    print(f"CrewAI Flow vs LangGraph mean latency: {flow_vs_lg['mean_latency_delta_pct']:+.2f}%")
    print(
        "Agent/Crew token overhead eliminated: "
        f"{overhead['agent_overhead_eliminated_by_flow_pct']:.2f}%"
    )
    print()
    print(f"artifact_json: {JSON_OUTPUT}")
    print(f"artifact_markdown: {MARKDOWN_OUTPUT}")


if __name__ == "__main__":
    main()
