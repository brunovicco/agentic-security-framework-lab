"""Compare four agentic framework benchmark variants under shared controls."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

LANGGRAPH_PATH = Path("artifacts/benchmarks/langgraph/latest.json")
CREWAI_AGENT_PATH = Path("artifacts/benchmarks/crewai/latest.json")
CREWAI_FLOW_PATH = Path("artifacts/benchmarks/crewai-flow/latest.json")
LLAMAINDEX_WORKFLOW_PATH = Path("artifacts/benchmarks/llamaindex-workflow/latest.json")

OUTPUT_DIR = Path("artifacts/benchmarks/comparison")
JSON_OUTPUT = OUTPUT_DIR / "four-way-latest.json"
MARKDOWN_OUTPUT = OUTPUT_DIR / "four-way-latest.md"

EXPECTED_VARIANTS = {
    "langgraph": ("langgraph", "evaluator_optimizer"),
    "crewai_agent": ("crewai", "single_agent_external_evaluator_optimizer"),
    "crewai_flow": ("crewai", "flow_direct_llm_evaluator_optimizer"),
    "llamaindex_workflow": (
        "llamaindex",
        "workflow_structured_predict_evaluator_optimizer",
    ),
}


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
    return {
        cast(str, item["scenario_id"])
        for item in cast(list[dict[str, Any]], payload["scenario_summaries"])
    }


def scenario_map(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Index scenario summaries by identifier."""
    summaries = cast(list[dict[str, Any]], payload["scenario_summaries"])
    return {cast(str, item["scenario_id"]): item for item in summaries}


def validate_comparability(artifacts: dict[str, dict[str, Any]]) -> None:
    """Fail closed unless all four benchmark artifacts are directly comparable."""
    models = {cast(str, payload["model"]) for payload in artifacts.values()}
    if len(models) != 1:
        raise RuntimeError(f"Benchmark models differ: {sorted(models)}")

    repetitions = {cast(int, payload["repetitions_per_scenario"]) for payload in artifacts.values()}
    if repetitions != {3}:
        raise RuntimeError("Expected three repetitions per scenario for every benchmark")

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

    llamaindex = artifacts["llamaindex_workflow"]
    if llamaindex.get("sampling") != "provider_default":
        raise RuntimeError("LlamaIndex Workflow benchmark must record provider-default sampling")


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
            float(candidate["mean_model_calls"]) - float(baseline["mean_model_calls"]),
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
        "total_tokens_delta": int(candidate["total_tokens"]) - int(baseline["total_tokens"]),
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
        raise RuntimeError("CrewAI Agent/Crew must exceed LangGraph tokens for overhead analysis")

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
    """Describe token overhead across the four benchmark variants."""
    lg_tokens = float(overalls["langgraph"]["mean_total_tokens"])
    agent_tokens = float(overalls["crewai_agent"]["mean_total_tokens"])
    flow_tokens = float(overalls["crewai_flow"]["mean_total_tokens"])
    llama_tokens = float(overalls["llamaindex_workflow"]["mean_total_tokens"])

    original_excess = agent_tokens - lg_tokens
    if original_excess <= 0:
        raise RuntimeError("Agent/Crew token excess must be positive")

    lighter_min = min(flow_tokens, llama_tokens)
    lighter_max = max(flow_tokens, llama_tokens)

    return {
        "langgraph_mean_tokens": lg_tokens,
        "crewai_agent_mean_tokens": agent_tokens,
        "crewai_flow_mean_tokens": flow_tokens,
        "llamaindex_workflow_mean_tokens": llama_tokens,
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
        "flow_vs_llamaindex_mean_token_difference": round(
            flow_tokens - llama_tokens,
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
        "first_attempt_acceptance_rate": summary["first_attempt_acceptance_rate"],
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
    """Build scenario-level four-way comparisons."""
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
    """Build the persisted four-way comparison payload."""
    overalls = {
        name: cast(dict[str, Any], payload["overall_summary"])
        for name, payload in artifacts.items()
    }

    return {
        "schema_version": "1",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "comparison": ("langgraph_vs_crewai_agent_vs_crewai_flow_vs_llamaindex_workflow"),
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
            "latency_interpretation": (
                "Mean and p50 are the primary descriptive latency metrics. "
                "With fifteen observations, nearest-rank p95 resolves to the "
                "sample maximum and is reported only as a small-sample tail indicator."
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
        "comparisons": {
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
        },
        "token_overhead_analysis": build_token_analysis(overalls),
        "scenario_comparison": build_scenario_comparison(artifacts),
        "limitations": [
            "The benchmark uses five synthetic scenarios and three repetitions per scenario.",
            (
                "Latency values are descriptive and must not be interpreted as "
                "production SLO evidence."
            ),
            (
                "At n=15, nearest-rank p95 resolves to the sample maximum, so "
                "mean and p50 are more useful for this comparison."
            ),
            (
                "The adversarial asset-id scenario is a narrow instruction/data-boundary "
                "test and is not evidence of general prompt-injection resistance."
            ),
            (
                "All variants share application-owned deterministic validation, retry, "
                "fallback, policy, dataset, and expected truth while intentionally using "
                "different framework orchestration abstractions."
            ),
            (
                "Token usage represents end-to-end framework-specific prompt and "
                "orchestration behavior for this workload."
            ),
            (
                "The sample is too small to support statistical-significance claims or "
                "general framework rankings."
            ),
        ],
    }


def render_markdown(payload: dict[str, Any]) -> str:
    """Render the human-readable four-way comparison."""
    variants = cast(dict[str, dict[str, Any]], payload["variants"])
    comparisons = cast(dict[str, dict[str, Any]], payload["comparisons"])
    token_analysis = cast(dict[str, Any], payload["token_overhead_analysis"])

    lg = variants["langgraph"]
    agent = variants["crewai_agent"]
    flow = variants["crewai_flow"]
    llama = variants["llamaindex_workflow"]

    llama_vs_lg = comparisons["llamaindex_workflow_vs_langgraph"]
    llama_vs_flow = comparisons["llamaindex_workflow_vs_crewai_flow"]
    llama_vs_agent = comparisons["llamaindex_workflow_vs_crewai_agent"]
    flow_vs_lg = comparisons["crewai_flow_vs_langgraph"]
    agent_vs_lg = comparisons["crewai_agent_vs_langgraph"]

    flow_overhead = cast(dict[str, Any], token_analysis["crewai_flow"])
    llama_overhead = cast(dict[str, Any], token_analysis["llamaindex_workflow"])

    lines = [
        "# Four-Way Agentic Framework Benchmark",
        "",
        "## Methodology",
        "",
        f"- Model: `{payload['methodology']['model']}`",
        "- Scenarios: 5",
        "- Repetitions per scenario: 3",
        "- Runs per variant: 15",
        "- Shared dataset and expected truth: yes",
        "- Shared deterministic evaluator, retry, fallback, and human-review policy: yes",
        "- Sampling: provider default",
        "- CrewAI Flow execution: headless",
        "- LlamaIndex Workflow execution: native async",
        "",
        "## Overall results",
        "",
        ("| Metric | LangGraph | CrewAI Agent/Crew | CrewAI Flow | LlamaIndex Workflow |"),
        "| --- | ---: | ---: | ---: | ---: |",
        (
            f"| Expected accuracy | {lg['expected_accuracy']:.1%} | "
            f"{agent['expected_accuracy']:.1%} | {flow['expected_accuracy']:.1%} | "
            f"{llama['expected_accuracy']:.1%} |"
        ),
        (
            f"| First-attempt acceptance | {lg['first_attempt_acceptance_rate']:.1%} | "
            f"{agent['first_attempt_acceptance_rate']:.1%} | "
            f"{flow['first_attempt_acceptance_rate']:.1%} | "
            f"{llama['first_attempt_acceptance_rate']:.1%} |"
        ),
        (
            f"| Mean model calls | {lg['mean_model_calls']:.2f} | "
            f"{agent['mean_model_calls']:.2f} | {flow['mean_model_calls']:.2f} | "
            f"{llama['mean_model_calls']:.2f} |"
        ),
        (
            f"| Mean latency | {lg['mean_latency_ms']:.2f} ms | "
            f"{agent['mean_latency_ms']:.2f} ms | {flow['mean_latency_ms']:.2f} ms | "
            f"{llama['mean_latency_ms']:.2f} ms |"
        ),
        (
            f"| p50 latency | {lg['p50_latency_ms']:.2f} ms | "
            f"{agent['p50_latency_ms']:.2f} ms | {flow['p50_latency_ms']:.2f} ms | "
            f"{llama['p50_latency_ms']:.2f} ms |"
        ),
        (
            f"| p95 latency* | {lg['p95_latency_ms']:.2f} ms | "
            f"{agent['p95_latency_ms']:.2f} ms | {flow['p95_latency_ms']:.2f} ms | "
            f"{llama['p95_latency_ms']:.2f} ms |"
        ),
        (
            f"| Mean total tokens | {lg['mean_total_tokens']:.2f} | "
            f"{agent['mean_total_tokens']:.2f} | {flow['mean_total_tokens']:.2f} | "
            f"{llama['mean_total_tokens']:.2f} |"
        ),
        (
            f"| Total tokens | {lg['total_tokens']} | {agent['total_tokens']} | "
            f"{flow['total_tokens']} | {llama['total_tokens']} |"
        ),
        "",
        "\\* At n=15, nearest-rank p95 is the sample maximum and is not a stable tail estimate.",
        "",
        "## Key comparisons",
        "",
        (
            f"- CrewAI Agent/Crew vs LangGraph mean tokens: "
            f"**{agent_vs_lg['mean_total_tokens_delta_pct']:+.2f}%**"
        ),
        (
            f"- CrewAI Flow vs LangGraph mean tokens: "
            f"**{flow_vs_lg['mean_total_tokens_delta_pct']:+.2f}%**"
        ),
        (
            f"- LlamaIndex Workflow vs LangGraph mean tokens: "
            f"**{llama_vs_lg['mean_total_tokens_delta_pct']:+.2f}%**"
        ),
        (
            f"- LlamaIndex Workflow vs CrewAI Flow mean tokens: "
            f"**{llama_vs_flow['mean_total_tokens_delta_pct']:+.2f}%**"
        ),
        (
            f"- LlamaIndex Workflow vs CrewAI Agent/Crew mean tokens: "
            f"**{llama_vs_agent['mean_total_tokens_delta_pct']:+.2f}%**"
        ),
        "",
        (
            f"CrewAI Flow eliminated **{flow_overhead['agent_overhead_eliminated_pct']:.2f}%** "
            "of the Agent/Crew token excess above LangGraph."
        ),
        (
            f"LlamaIndex Workflow eliminated "
            f"**{llama_overhead['agent_overhead_eliminated_pct']:.2f}%** of the same excess."
        ),
        (
            f"The two lighter orchestration variants differ by only "
            f"**{token_analysis['flow_vs_llamaindex_mean_token_difference']:.2f} tokens/run** "
            f"(**{token_analysis['lighter_orchestration_token_spread_pct']:.2f}% spread**)."
        ),
        "",
        "## LlamaIndex Workflow latency deltas",
        "",
        (
            f"- vs LangGraph: mean **{llama_vs_lg['mean_latency_delta_pct']:+.2f}%**, "
            f"p50 **{llama_vs_lg['p50_latency_delta_pct']:+.2f}%**"
        ),
        (
            f"- vs CrewAI Flow: mean **{llama_vs_flow['mean_latency_delta_pct']:+.2f}%**, "
            f"p50 **{llama_vs_flow['p50_latency_delta_pct']:+.2f}%**"
        ),
        (
            f"- vs CrewAI Agent/Crew: mean "
            f"**{llama_vs_agent['mean_latency_delta_pct']:+.2f}%**, "
            f"p50 **{llama_vs_agent['p50_latency_delta_pct']:+.2f}%**"
        ),
        "",
        "## Scenario mean tokens",
        "",
        "| Scenario | LangGraph | CrewAI Agent/Crew | CrewAI Flow | LlamaIndex Workflow |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]

    scenarios = cast(list[dict[str, Any]], payload["scenario_comparison"])
    for scenario in scenarios:
        lines.append(
            f"| {scenario['scenario_id']} | "
            f"{scenario['langgraph']['mean_total_tokens']:.2f} | "
            f"{scenario['crewai_agent']['mean_total_tokens']:.2f} | "
            f"{scenario['crewai_flow']['mean_total_tokens']:.2f} | "
            f"{scenario['llamaindex_workflow']['mean_total_tokens']:.2f} |"
        )

    lines.extend(
        [
            "",
            "## Scenario p50 latency",
            "",
            ("| Scenario | LangGraph | CrewAI Agent/Crew | CrewAI Flow | LlamaIndex Workflow |"),
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )

    for scenario in scenarios:
        lines.append(
            f"| {scenario['scenario_id']} | "
            f"{scenario['langgraph']['p50_latency_ms']:.2f} ms | "
            f"{scenario['crewai_agent']['p50_latency_ms']:.2f} ms | "
            f"{scenario['crewai_flow']['p50_latency_ms']:.2f} ms | "
            f"{scenario['llamaindex_workflow']['p50_latency_ms']:.2f} ms |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            (
                "Under this controlled small benchmark, both CrewAI Flow with a direct "
                "structured LLM call and LlamaIndex Workflows with `structured_predict()` "
                "landed very close to the LangGraph token baseline."
            ),
            "",
            (
                "The much larger Agent/Task/Crew token footprint therefore should not be "
                "generalized to CrewAI as a framework. For this workload, the selected "
                "orchestration abstraction had a larger effect on token consumption than "
                "the difference between the lighter framework implementations."
            ),
            "",
            (
                "All four official variants reached 100% expected accuracy and 100% "
                "first-attempt acceptance in these fifteen-run samples, so this benchmark "
                "does not establish a quality ranking among the frameworks."
            ),
            "",
            (
                "The adversarial asset-ID scenario remains a narrow instruction/data-boundary "
                "test and is not evidence of general prompt-injection resistance."
            ),
            "",
            (
                "Latency is descriptive only. No statistical-significance or production-SLO "
                "claim should be made from these samples."
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
    """Validate inputs and write machine- and human-readable comparison artifacts."""
    artifacts = {
        "langgraph": load_json(LANGGRAPH_PATH),
        "crewai_agent": load_json(CREWAI_AGENT_PATH),
        "crewai_flow": load_json(CREWAI_FLOW_PATH),
        "llamaindex_workflow": load_json(LLAMAINDEX_WORKFLOW_PATH),
    }

    validate_comparability(artifacts)
    payload = build_payload(artifacts)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    JSON_OUTPUT.write_text(json.dumps(payload, indent=2) + "\n")
    MARKDOWN_OUTPUT.write_text(render_markdown(payload))

    comparisons = cast(dict[str, dict[str, Any]], payload["comparisons"])
    token_analysis = cast(dict[str, Any], payload["token_overhead_analysis"])

    print("Four-way benchmark comparison generated.")
    print(f"artifact_json: {JSON_OUTPUT}")
    print(f"artifact_markdown: {MARKDOWN_OUTPUT}")
    print()
    print(
        "LlamaIndex vs LangGraph tokens:       "
        f"{comparisons['llamaindex_workflow_vs_langgraph']['mean_total_tokens_delta_pct']:+.2f}%"
    )
    print(
        "LlamaIndex vs CrewAI Flow tokens:     "
        f"{comparisons['llamaindex_workflow_vs_crewai_flow']['mean_total_tokens_delta_pct']:+.2f}%"
    )
    print(
        "LlamaIndex vs Agent/Crew tokens:      "
        f"{comparisons['llamaindex_workflow_vs_crewai_agent']['mean_total_tokens_delta_pct']:+.2f}%"
    )
    print(
        "LlamaIndex vs LangGraph mean latency: "
        f"{comparisons['llamaindex_workflow_vs_langgraph']['mean_latency_delta_pct']:+.2f}%"
    )
    print(
        "LlamaIndex vs CrewAI Flow latency:    "
        f"{comparisons['llamaindex_workflow_vs_crewai_flow']['mean_latency_delta_pct']:+.2f}%"
    )
    print(
        "LlamaIndex Agent overhead eliminated: "
        f"{token_analysis['llamaindex_workflow']['agent_overhead_eliminated_pct']:.2f}%"
    )


if __name__ == "__main__":
    main()
