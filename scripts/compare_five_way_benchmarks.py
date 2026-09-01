"""Compare five agentic framework benchmark variants under shared controls."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

LANGGRAPH_PATH = Path("artifacts/benchmarks/langgraph/latest.json")
CREWAI_AGENT_PATH = Path("artifacts/benchmarks/crewai/latest.json")
CREWAI_FLOW_PATH = Path("artifacts/benchmarks/crewai-flow/latest.json")
LLAMAINDEX_WORKFLOW_PATH = Path(
    "artifacts/benchmarks/llamaindex-workflow/latest.json"
)
AGNO_WORKFLOW_PATH = Path("artifacts/benchmarks/agno-workflow/latest.json")

OUTPUT_DIR = Path("artifacts/benchmarks/comparison")
JSON_OUTPUT = OUTPUT_DIR / "five-way-latest.json"
MARKDOWN_OUTPUT = OUTPUT_DIR / "five-way-latest.md"

EXPECTED_VARIANTS = {
    "langgraph": ("langgraph", "evaluator_optimizer"),
    "crewai_agent": (
        "crewai",
        "single_agent_external_evaluator_optimizer",
    ),
    "crewai_flow": (
        "crewai",
        "flow_direct_llm_evaluator_optimizer",
    ),
    "llamaindex_workflow": (
        "llamaindex",
        "workflow_structured_predict_evaluator_optimizer",
    ),
    "agno_workflow": (
        "agno",
        "workflow_loop_condition_evaluator_optimizer",
    ),
}

VARIANT_ORDER = (
    "langgraph",
    "crewai_agent",
    "crewai_flow",
    "llamaindex_workflow",
    "agno_workflow",
)


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


def percentage_point_delta(candidate: float, baseline: float) -> float:
    """Calculate percentage-point difference for rate metrics."""
    return round((candidate - baseline) * 100.0, 2)


def ratio(candidate: float, baseline: float) -> float:
    """Calculate candidate-to-baseline ratio."""
    if baseline == 0:
        raise RuntimeError("Cannot calculate ratio from zero")
    return round(candidate / baseline, 3)


def scenario_ids(payload: dict[str, Any]) -> set[str]:
    """Return scenario identifiers from one artifact."""
    summaries = cast(list[dict[str, Any]], payload["scenario_summaries"])
    return {cast(str, item["scenario_id"]) for item in summaries}


def scenario_map(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Index scenario summaries by identifier."""
    summaries = cast(list[dict[str, Any]], payload["scenario_summaries"])
    return {cast(str, item["scenario_id"]): item for item in summaries}


def validate_comparability(artifacts: dict[str, dict[str, Any]]) -> None:
    """Fail closed unless all five benchmark artifacts are comparable."""
    models = {cast(str, payload["model"]) for payload in artifacts.values()}
    if len(models) != 1:
        raise RuntimeError(f"Benchmark models differ: {sorted(models)}")

    repetitions = {
        cast(int, payload["repetitions_per_scenario"])
        for payload in artifacts.values()
    }
    if repetitions != {3}:
        raise RuntimeError(
            "Expected three repetitions per scenario for every benchmark"
        )

    expected_scenarios: set[str] | None = None
    for name, payload in artifacts.items():
        overall = cast(dict[str, Any], payload["overall_summary"])
        if overall["scenarios"] != 5:
            raise RuntimeError(f"{name} does not contain exactly five scenarios")
        if overall["total_runs"] != 15:
            raise RuntimeError(f"{name} does not contain exactly fifteen runs")

        current_scenarios = scenario_ids(payload)
        if expected_scenarios is None:
            expected_scenarios = current_scenarios
        elif current_scenarios != expected_scenarios:
            raise RuntimeError(f"{name} scenario identifiers differ")

        expected_framework, expected_pattern = EXPECTED_VARIANTS[name]
        if payload["framework"] != expected_framework:
            raise RuntimeError(f"Unexpected framework identifier for {name}")
        if payload["pattern"] != expected_pattern:
            raise RuntimeError(f"Unexpected pattern identifier for {name}")

    for name in ("llamaindex_workflow", "agno_workflow"):
        if artifacts[name].get("sampling") != "provider_default":
            raise RuntimeError(
                f"{name} benchmark must record provider-default sampling"
            )


def comparison_metrics(
    candidate: dict[str, Any],
    baseline: dict[str, Any],
) -> dict[str, Any]:
    """Compare two overall benchmark summaries."""
    return {
        "expected_accuracy_delta_percentage_points": percentage_point_delta(
            float(candidate["expected_accuracy"]),
            float(baseline["expected_accuracy"]),
        ),
        "first_attempt_acceptance_delta_percentage_points": percentage_point_delta(
            float(candidate["first_attempt_acceptance_rate"]),
            float(baseline["first_attempt_acceptance_rate"]),
        ),
        "retry_rate_delta_percentage_points": percentage_point_delta(
            float(candidate["retry_rate"]),
            float(baseline["retry_rate"]),
        ),
        "fallback_rate_delta_percentage_points": percentage_point_delta(
            float(candidate["fallback_rate"]),
            float(baseline["fallback_rate"]),
        ),
        "mean_model_calls_delta": round(
            float(candidate["mean_model_calls"])
            - float(baseline["mean_model_calls"]),
            2,
        ),
        "mean_latency_delta_pct": percent_delta(
            float(candidate["mean_latency_ms"]),
            float(baseline["mean_latency_ms"]),
        ),
        "p50_latency_delta_pct": percent_delta(
            float(candidate["p50_latency_ms"]),
            float(baseline["p50_latency_ms"]),
        ),
        "p95_latency_delta_pct": percent_delta(
            float(candidate["p95_latency_ms"]),
            float(baseline["p95_latency_ms"]),
        ),
        "mean_total_tokens_delta_pct": percent_delta(
            float(candidate["mean_total_tokens"]),
            float(baseline["mean_total_tokens"]),
        ),
        "token_ratio": ratio(
            float(candidate["mean_total_tokens"]),
            float(baseline["mean_total_tokens"]),
        ),
        "total_tokens_delta": int(candidate["total_tokens"])
        - int(baseline["total_tokens"]),
    }


def overhead_elimination(
    *,
    langgraph_tokens: float,
    agent_tokens: float,
    candidate_tokens: float,
) -> dict[str, float]:
    """Quantify how much Agent/Crew excess a lighter abstraction removes."""
    original_excess = agent_tokens - langgraph_tokens
    if original_excess <= 0:
        raise RuntimeError(
            "CrewAI Agent/Crew must exceed LangGraph tokens for overhead analysis"
        )

    candidate_excess = candidate_tokens - langgraph_tokens
    eliminated = agent_tokens - candidate_tokens
    return {
        "candidate_mean_tokens": candidate_tokens,
        "candidate_excess_vs_langgraph_tokens": round(candidate_excess, 2),
        "tokens_removed_vs_agent": round(eliminated, 2),
        "agent_overhead_eliminated_pct": round(
            (eliminated / original_excess) * 100.0,
            2,
        ),
    }


def build_token_analysis(overalls: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Describe token overhead across the five benchmark variants."""
    lg_tokens = float(overalls["langgraph"]["mean_total_tokens"])
    agent_tokens = float(overalls["crewai_agent"]["mean_total_tokens"])
    flow_tokens = float(overalls["crewai_flow"]["mean_total_tokens"])
    llama_tokens = float(overalls["llamaindex_workflow"]["mean_total_tokens"])
    agno_tokens = float(overalls["agno_workflow"]["mean_total_tokens"])

    original_excess = agent_tokens - lg_tokens
    if original_excess <= 0:
        raise RuntimeError("Agent/Crew token excess must be positive")

    lighter_tokens = (flow_tokens, llama_tokens, agno_tokens)
    lighter_min = min(lighter_tokens)
    lighter_max = max(lighter_tokens)

    return {
        "langgraph_mean_tokens": lg_tokens,
        "crewai_agent_mean_tokens": agent_tokens,
        "crewai_flow_mean_tokens": flow_tokens,
        "llamaindex_workflow_mean_tokens": llama_tokens,
        "agno_workflow_mean_tokens": agno_tokens,
        "agent_excess_vs_langgraph_tokens": round(original_excess, 2),
        "crewai_flow": overhead_elimination(
            langgraph_tokens=lg_tokens,
            agent_tokens=agent_tokens,
            candidate_tokens=flow_tokens,
        ),
        "llamaindex_workflow": overhead_elimination(
            langgraph_tokens=lg_tokens,
            agent_tokens=agent_tokens,
            candidate_tokens=llama_tokens,
        ),
        "agno_workflow": overhead_elimination(
            langgraph_tokens=lg_tokens,
            agent_tokens=agent_tokens,
            candidate_tokens=agno_tokens,
        ),
        "flow_vs_llamaindex_mean_token_difference": round(
            flow_tokens - llama_tokens,
            2,
        ),
        "agno_vs_flow_mean_token_difference": round(
            agno_tokens - flow_tokens,
            2,
        ),
        "agno_vs_llamaindex_mean_token_difference": round(
            agno_tokens - llama_tokens,
            2,
        ),
        "lighter_orchestration_token_spread_pct": percent_delta(
            lighter_max,
            lighter_min,
        ),
    }


def slim_scenario(summary: dict[str, Any]) -> dict[str, Any]:
    """Return the scenario metrics used in the cross-framework report."""
    return {
        "expected_accuracy": summary["expected_accuracy"],
        "first_attempt_acceptance_rate": summary[
            "first_attempt_acceptance_rate"
        ],
        "retry_rate": summary["retry_rate"],
        "fallback_rate": summary["fallback_rate"],
        "mean_model_calls": summary["mean_model_calls"],
        "mean_latency_ms": summary["mean_latency_ms"],
        "p50_latency_ms": summary["p50_latency_ms"],
        "p95_latency_ms": summary["p95_latency_ms"],
        "mean_total_tokens": summary["mean_total_tokens"],
    }


def build_scenario_comparison(
    artifacts: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build scenario-level five-way comparisons."""
    maps = {name: scenario_map(payload) for name, payload in artifacts.items()}
    ordered_ids = [
        cast(str, item["scenario_id"])
        for item in cast(
            list[dict[str, Any]],
            artifacts["langgraph"]["scenario_summaries"],
        )
    ]

    result: list[dict[str, Any]] = []
    for scenario_id in ordered_ids:
        entry: dict[str, Any] = {"scenario_id": scenario_id}
        for name, mapping in maps.items():
            entry[name] = slim_scenario(mapping[scenario_id])
        result.append(entry)
    return result


def build_payload(artifacts: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Build the persisted five-way comparison payload."""
    overalls = {
        name: cast(dict[str, Any], payload["overall_summary"])
        for name, payload in artifacts.items()
    }

    comparisons = {
        "crewai_agent_vs_langgraph": comparison_metrics(
            overalls["crewai_agent"], overalls["langgraph"]
        ),
        "crewai_flow_vs_langgraph": comparison_metrics(
            overalls["crewai_flow"], overalls["langgraph"]
        ),
        "crewai_flow_vs_crewai_agent": comparison_metrics(
            overalls["crewai_flow"], overalls["crewai_agent"]
        ),
        "llamaindex_workflow_vs_langgraph": comparison_metrics(
            overalls["llamaindex_workflow"], overalls["langgraph"]
        ),
        "llamaindex_workflow_vs_crewai_flow": comparison_metrics(
            overalls["llamaindex_workflow"], overalls["crewai_flow"]
        ),
        "llamaindex_workflow_vs_crewai_agent": comparison_metrics(
            overalls["llamaindex_workflow"], overalls["crewai_agent"]
        ),
        "agno_workflow_vs_langgraph": comparison_metrics(
            overalls["agno_workflow"], overalls["langgraph"]
        ),
        "agno_workflow_vs_crewai_flow": comparison_metrics(
            overalls["agno_workflow"], overalls["crewai_flow"]
        ),
        "agno_workflow_vs_llamaindex_workflow": comparison_metrics(
            overalls["agno_workflow"], overalls["llamaindex_workflow"]
        ),
        "agno_workflow_vs_crewai_agent": comparison_metrics(
            overalls["agno_workflow"], overalls["crewai_agent"]
        ),
    }

    return {
        "schema_version": "1",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "comparison": (
            "langgraph_vs_crewai_agent_vs_crewai_flow_vs_"
            "llamaindex_workflow_vs_agno_workflow"
        ),
        "methodology": {
            "model": artifacts["langgraph"]["model"],
            "scenarios": 5,
            "repetitions_per_scenario": 3,
            "runs_per_variant": 15,
            "shared_dataset": True,
            "shared_expected_truth": True,
            "shared_deterministic_validation": True,
            "shared_bounded_retry": True,
            "shared_oracle_fallback": True,
            "shared_human_review_policy": True,
            "sampling_policy": "provider_default",
            "crewai_flow_headless": True,
            "llamaindex_native_async_execution": True,
            "agno_native_sync_execution": True,
            "latency_interpretation": (
                "Mean and p50 are the primary descriptive latency metrics. "
                "With fifteen observations, nearest-rank p95 resolves to the "
                "sample maximum and is only a small-sample tail indicator."
            ),
        },
        "variants": {
            name: {
                "framework": artifacts[name]["framework"],
                "pattern": artifacts[name]["pattern"],
                **overall,
            }
            for name, overall in overalls.items()
        },
        "comparisons": comparisons,
        "token_overhead_analysis": build_token_analysis(overalls),
        "scenario_comparison": build_scenario_comparison(artifacts),
        "limitations": [
            (
                "The benchmark uses five synthetic scenarios and three "
                "repetitions per scenario."
            ),
            (
                "Latency values are descriptive and must not be interpreted "
                "as production SLO evidence."
            ),
            (
                "At n=15, nearest-rank p95 resolves to the sample maximum, "
                "so mean and p50 are more useful for this comparison."
            ),
            (
                "The adversarial asset-id scenario is a narrow "
                "instruction/data-boundary test and is not evidence of "
                "general prompt-injection resistance."
            ),
            (
                "All variants share application-owned deterministic "
                "validation, retry, fallback, policy, dataset, and expected "
                "truth while intentionally using different framework "
                "orchestration abstractions."
            ),
            (
                "Token usage represents end-to-end framework-specific prompt "
                "and orchestration behavior for this workload."
            ),
            (
                "The sample is too small to support statistical-significance "
                "claims or general framework rankings."
            ),
        ],
    }


def metric_row(
    label: str,
    key: str,
    variants: dict[str, dict[str, Any]],
    *,
    suffix: str = "",
) -> str:
    """Render one numeric row in stable variant order."""
    values = [
        f"{float(variants[name][key]):.2f}{suffix}" for name in VARIANT_ORDER
    ]
    return f"| {label} | " + " | ".join(values) + " |"


def render_markdown(payload: dict[str, Any]) -> str:
    """Render the human-readable five-way comparison."""
    variants = cast(dict[str, dict[str, Any]], payload["variants"])
    comparisons = cast(dict[str, dict[str, Any]], payload["comparisons"])
    token_analysis = cast(dict[str, Any], payload["token_overhead_analysis"])

    agno_vs_lg = comparisons["agno_workflow_vs_langgraph"]
    agno_vs_flow = comparisons["agno_workflow_vs_crewai_flow"]
    agno_vs_llama = comparisons["agno_workflow_vs_llamaindex_workflow"]
    agno_vs_agent = comparisons["agno_workflow_vs_crewai_agent"]
    agno_overhead = cast(dict[str, Any], token_analysis["agno_workflow"])

    lines = [
        "# Five-Way Agentic Framework Benchmark",
        "",
        "## Methodology",
        "",
        f"- Model: `{payload['methodology']['model']}`",
        "- Scenarios: 5",
        "- Repetitions per scenario: 3",
        "- Runs per variant: 15",
        "- Shared dataset and expected truth: yes",
        (
            "- Shared deterministic evaluator, retry, fallback, and "
            "human-review policy: yes"
        ),
        "- Sampling: provider default",
        "- CrewAI Flow execution: headless",
        "- LlamaIndex Workflow execution: native async",
        "- Agno Workflow execution: native sync",
        "",
        "## Overall results",
        "",
        (
            "| Metric | LangGraph | CrewAI Agent/Crew | CrewAI Flow | "
            "LlamaIndex Workflow | Agno Workflow |"
        ),
        "| --- | ---: | ---: | ---: | ---: | ---: |",
        (
            "| Expected accuracy | "
            + " | ".join(
                f"{variants[name]['expected_accuracy']:.1%}"
                for name in VARIANT_ORDER
            )
            + " |"
        ),
        (
            "| First-attempt acceptance | "
            + " | ".join(
                f"{variants[name]['first_attempt_acceptance_rate']:.1%}"
                for name in VARIANT_ORDER
            )
            + " |"
        ),
        metric_row("Mean model calls", "mean_model_calls", variants),
        metric_row("Mean latency", "mean_latency_ms", variants, suffix=" ms"),
        metric_row("p50 latency", "p50_latency_ms", variants, suffix=" ms"),
        metric_row("p95 latency*", "p95_latency_ms", variants, suffix=" ms"),
        metric_row("Mean total tokens", "mean_total_tokens", variants),
        (
            "| Total tokens | "
            + " | ".join(
                str(variants[name]["total_tokens"]) for name in VARIANT_ORDER
            )
            + " |"
        ),
        "",
        (
            "\\* At n=15, nearest-rank p95 is the sample maximum and is "
            "not a stable tail estimate."
        ),
        "",
        "## Agno Workflow comparisons",
        "",
        (
            f"- vs LangGraph tokens: "
            f"**{agno_vs_lg['mean_total_tokens_delta_pct']:+.2f}%**"
        ),
        (
            f"- vs CrewAI Flow tokens: "
            f"**{agno_vs_flow['mean_total_tokens_delta_pct']:+.2f}%**"
        ),
        (
            f"- vs LlamaIndex Workflow tokens: "
            f"**{agno_vs_llama['mean_total_tokens_delta_pct']:+.2f}%**"
        ),
        (
            f"- vs CrewAI Agent/Crew tokens: "
            f"**{agno_vs_agent['mean_total_tokens_delta_pct']:+.2f}%**"
        ),
        "",
        (
            f"Agno Workflow eliminated "
            f"**{agno_overhead['agent_overhead_eliminated_pct']:.2f}%** "
            "of the Agent/Crew token excess above LangGraph."
        ),
        (
            "The three lighter orchestration variants have a token spread "
            f"of only **{token_analysis['lighter_orchestration_token_spread_pct']:.2f}%**."
        ),
        (
            f"Agno differs from CrewAI Flow by "
            f"**{token_analysis['agno_vs_flow_mean_token_difference']:.2f} "
            "tokens/run** and from LlamaIndex Workflow by "
            f"**{token_analysis['agno_vs_llamaindex_mean_token_difference']:.2f} "
            "tokens/run**."
        ),
        "",
        "## Agno Workflow latency deltas",
        "",
        (
            f"- vs LangGraph: mean "
            f"**{agno_vs_lg['mean_latency_delta_pct']:+.2f}%**, "
            f"p50 **{agno_vs_lg['p50_latency_delta_pct']:+.2f}%**"
        ),
        (
            f"- vs CrewAI Flow: mean "
            f"**{agno_vs_flow['mean_latency_delta_pct']:+.2f}%**, "
            f"p50 **{agno_vs_flow['p50_latency_delta_pct']:+.2f}%**"
        ),
        (
            f"- vs LlamaIndex Workflow: mean "
            f"**{agno_vs_llama['mean_latency_delta_pct']:+.2f}%**, "
            f"p50 **{agno_vs_llama['p50_latency_delta_pct']:+.2f}%**"
        ),
        (
            f"- vs CrewAI Agent/Crew: mean "
            f"**{agno_vs_agent['mean_latency_delta_pct']:+.2f}%**, "
            f"p50 **{agno_vs_agent['p50_latency_delta_pct']:+.2f}%**"
        ),
        "",
        "## Scenario mean tokens",
        "",
        (
            "| Scenario | LangGraph | CrewAI Agent/Crew | CrewAI Flow | "
            "LlamaIndex Workflow | Agno Workflow |"
        ),
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]

    scenarios = cast(list[dict[str, Any]], payload["scenario_comparison"])
    for scenario in scenarios:
        lines.append(
            f"| {scenario['scenario_id']} | "
            f"{scenario['langgraph']['mean_total_tokens']:.2f} | "
            f"{scenario['crewai_agent']['mean_total_tokens']:.2f} | "
            f"{scenario['crewai_flow']['mean_total_tokens']:.2f} | "
            f"{scenario['llamaindex_workflow']['mean_total_tokens']:.2f} | "
            f"{scenario['agno_workflow']['mean_total_tokens']:.2f} |"
        )

    lines.extend(
        [
            "",
            "## Scenario p50 latency",
            "",
            (
                "| Scenario | LangGraph | CrewAI Agent/Crew | CrewAI Flow | "
                "LlamaIndex Workflow | Agno Workflow |"
            ),
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )

    for scenario in scenarios:
        lines.append(
            f"| {scenario['scenario_id']} | "
            f"{scenario['langgraph']['p50_latency_ms']:.2f} ms | "
            f"{scenario['crewai_agent']['p50_latency_ms']:.2f} ms | "
            f"{scenario['crewai_flow']['p50_latency_ms']:.2f} ms | "
            f"{scenario['llamaindex_workflow']['p50_latency_ms']:.2f} ms | "
            f"{scenario['agno_workflow']['p50_latency_ms']:.2f} ms |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            (
                "Under this controlled small benchmark, CrewAI Flow, "
                "LlamaIndex Workflow, and Agno Workflow all landed close to "
                "the LangGraph token baseline."
            ),
            "",
            (
                "The substantially larger Agent/Task/Crew token footprint "
                "therefore should not be generalized to CrewAI as a framework. "
                "For this workload, orchestration abstraction choice had a "
                "much larger effect on token consumption than the difference "
                "among the lighter implementations."
            ),
            "",
            (
                "Agno Workflow used slightly more tokens than CrewAI Flow and "
                "LlamaIndex Workflow, while showing higher mean and p50 latency "
                "in this fifteen-run sample. These latency results are "
                "descriptive only and do not establish a general framework ranking."
            ),
            "",
            (
                "All five official variants reached 100% expected accuracy and "
                "100% first-attempt acceptance, so this benchmark does not "
                "establish a quality ranking among frameworks."
            ),
            "",
            (
                "The adversarial asset-ID scenario remains a narrow "
                "instruction/data-boundary test and is not evidence of general "
                "prompt-injection resistance."
            ),
            "",
            "## Limitations",
            "",
        ]
    )

    for limitation in cast(list[str], payload["limitations"]):
        lines.append(f"- {limitation}")

    lines.append("")
    return "\n".join(lines)


def main() -> None:
    """Validate inputs and write five-way comparison artifacts."""
    artifacts = {
        "langgraph": load_json(LANGGRAPH_PATH),
        "crewai_agent": load_json(CREWAI_AGENT_PATH),
        "crewai_flow": load_json(CREWAI_FLOW_PATH),
        "llamaindex_workflow": load_json(LLAMAINDEX_WORKFLOW_PATH),
        "agno_workflow": load_json(AGNO_WORKFLOW_PATH),
    }

    validate_comparability(artifacts)
    payload = build_payload(artifacts)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    JSON_OUTPUT.write_text(json.dumps(payload, indent=2) + "\n")
    MARKDOWN_OUTPUT.write_text(render_markdown(payload))

    comparisons = cast(dict[str, dict[str, Any]], payload["comparisons"])
    token_analysis = cast(dict[str, Any], payload["token_overhead_analysis"])

    print("Five-way benchmark comparison generated.")
    print(f"artifact_json: {JSON_OUTPUT}")
    print(f"artifact_markdown: {MARKDOWN_OUTPUT}")
    print()
    print(
        "Agno vs LangGraph tokens:           "
        f"{comparisons['agno_workflow_vs_langgraph']['mean_total_tokens_delta_pct']:+.2f}%"
    )
    print(
        "Agno vs CrewAI Flow tokens:         "
        f"{comparisons['agno_workflow_vs_crewai_flow']['mean_total_tokens_delta_pct']:+.2f}%"
    )
    print(
        "Agno vs LlamaIndex tokens:          "
        f"{comparisons['agno_workflow_vs_llamaindex_workflow']['mean_total_tokens_delta_pct']:+.2f}%"
    )
    print(
        "Agno vs Agent/Crew tokens:          "
        f"{comparisons['agno_workflow_vs_crewai_agent']['mean_total_tokens_delta_pct']:+.2f}%"
    )
    print(
        "Agno vs LangGraph mean latency:     "
        f"{comparisons['agno_workflow_vs_langgraph']['mean_latency_delta_pct']:+.2f}%"
    )
    print(
        "Agno vs CrewAI Flow mean latency:   "
        f"{comparisons['agno_workflow_vs_crewai_flow']['mean_latency_delta_pct']:+.2f}%"
    )
    print(
        "Agno Agent overhead eliminated:     "
        f"{token_analysis['agno_workflow']['agent_overhead_eliminated_pct']:.2f}%"
    )
    print(
        "Lighter orchestration token spread: "
        f"{token_analysis['lighter_orchestration_token_spread_pct']:.2f}%"
    )


if __name__ == "__main__":
    main()
