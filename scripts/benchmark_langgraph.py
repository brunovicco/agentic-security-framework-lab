"""Benchmark the validated LangGraph vulnerability-analysis workflow."""

import argparse
import json
import math
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from statistics import mean, median
from time import perf_counter
from typing import Literal, cast

from langchain_core.callbacks import get_usage_metadata_callback
from langchain_core.messages import UsageMetadata

from agentic_lab.adapters.fixtures.demo import DEMO_CVE_ID
from agentic_lab.adapters.langchain.analyzer import (
    LangChainVulnerabilityAnalyzer,
)
from agentic_lab.adapters.langchain.model import create_chat_model, gateway_model_alias
from agentic_lab.adapters.langgraph.llm_graph import (
    run_llm_analysis_graph,
)


@dataclass(frozen=True, slots=True)
class TokenUsage:
    """Represent standardized token usage for one benchmark execution."""

    input_tokens: int
    output_tokens: int
    total_tokens: int


@dataclass(frozen=True, slots=True)
class BenchmarkRun:
    """Capture measurements for one LangGraph execution."""

    run: int
    model: str
    latency_ms: float
    analysis_source: Literal["llm", "oracle_fallback"]
    validation_passed: bool
    analysis_attempts: int
    model_calls: int
    confidence: float
    input_tokens: int
    output_tokens: int
    total_tokens: int


def parse_runs() -> int:
    """Parse and validate the requested number of benchmark runs."""
    parser = argparse.ArgumentParser(
        description="Benchmark the validated LangGraph workflow.",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=5,
        help="Number of LLM executions to perform.",
    )

    args = parser.parse_args()
    runs = cast(int, args.runs)

    if runs < 1:
        raise ValueError("--runs must be at least 1")

    return runs


def aggregate_usage(
    usage_by_model: Mapping[str, UsageMetadata],
) -> TokenUsage:
    """Aggregate standardized LangChain usage across model responses."""
    return TokenUsage(
        input_tokens=sum(usage["input_tokens"] for usage in usage_by_model.values()),
        output_tokens=sum(usage["output_tokens"] for usage in usage_by_model.values()),
        total_tokens=sum(usage["total_tokens"] for usage in usage_by_model.values()),
    )


def nearest_rank_percentile(
    values: list[float],
    percentile: float,
) -> float:
    """Calculate a percentile using the nearest-rank method."""
    if not values:
        raise ValueError("Percentile requires at least one value")

    if not 0 < percentile <= 1:
        raise ValueError("Percentile must be greater than 0 and at most 1")

    ordered = sorted(values)
    rank = math.ceil(percentile * len(ordered))

    return ordered[rank - 1]


def main() -> None:
    """Run repeated LangGraph analyses and summarize measurements."""
    requested_runs = parse_runs()
    model_name = gateway_model_alias()

    model = create_chat_model()
    analyzer = LangChainVulnerabilityAnalyzer(model)

    benchmark_runs: list[BenchmarkRun] = []

    for run_number in range(1, requested_runs + 1):
        started_at = perf_counter()

        with get_usage_metadata_callback() as usage_callback:
            output = run_llm_analysis_graph(
                analyzer=analyzer,
                cve_id=DEMO_CVE_ID,
            )

        latency_ms = (perf_counter() - started_at) * 1000
        usage = aggregate_usage(usage_callback.usage_metadata)
        result = output["result"]

        analysis_attempts = output["analysis_attempts"]

        benchmark_run = BenchmarkRun(
            run=run_number,
            model=model_name,
            latency_ms=round(latency_ms, 2),
            analysis_source=output["analysis_source"],
            validation_passed=output["validation_passed"],
            analysis_attempts=analysis_attempts,
            model_calls=analysis_attempts,
            confidence=result.confidence,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            total_tokens=usage.total_tokens,
        )

        benchmark_runs.append(benchmark_run)

        print(json.dumps(asdict(benchmark_run)))

    total_runs = len(benchmark_runs)

    accepted = sum(run.analysis_source == "llm" for run in benchmark_runs)
    fallbacks = total_runs - accepted

    first_attempt_accepts = sum(
        run.analysis_source == "llm" and run.analysis_attempts == 1 for run in benchmark_runs
    )

    retried = sum(run.analysis_attempts > 1 for run in benchmark_runs)

    recovered_after_retry = sum(
        run.analysis_attempts > 1 and run.analysis_source == "llm" for run in benchmark_runs
    )

    fallback_after_retry = sum(
        run.analysis_attempts > 1 and run.analysis_source == "oracle_fallback"
        for run in benchmark_runs
    )

    latencies = [run.latency_ms for run in benchmark_runs]

    recovery_rate = recovered_after_retry / retried if retried else 0.0

    summary = {
        "framework": "langgraph",
        "pattern": "evaluator_optimizer",
        "model": model_name,
        "runs": total_runs,
        "accepted": accepted,
        "fallbacks": fallbacks,
        "acceptance_rate": accepted / total_runs,
        "fallback_rate": fallbacks / total_runs,
        "first_attempt_acceptance_rate": (first_attempt_accepts / total_runs),
        "retried": retried,
        "retry_rate": retried / total_runs,
        "recovered_after_retry": recovered_after_retry,
        "recovery_rate": recovery_rate,
        "fallback_after_retry": fallback_after_retry,
        "mean_model_calls": round(
            mean(run.model_calls for run in benchmark_runs),
            2,
        ),
        "total_model_calls": sum(run.model_calls for run in benchmark_runs),
        "mean_latency_ms": round(
            mean(latencies),
            2,
        ),
        "p50_latency_ms": round(
            median(latencies),
            2,
        ),
        "p95_latency_ms": round(
            nearest_rank_percentile(
                latencies,
                0.95,
            ),
            2,
        ),
        "mean_confidence": round(
            mean(run.confidence for run in benchmark_runs),
            4,
        ),
        "mean_input_tokens": round(
            mean(run.input_tokens for run in benchmark_runs),
            2,
        ),
        "mean_output_tokens": round(
            mean(run.output_tokens for run in benchmark_runs),
            2,
        ),
        "mean_total_tokens": round(
            mean(run.total_tokens for run in benchmark_runs),
            2,
        ),
        "total_input_tokens": sum(run.input_tokens for run in benchmark_runs),
        "total_output_tokens": sum(run.output_tokens for run in benchmark_runs),
        "total_tokens": sum(run.total_tokens for run in benchmark_runs),
    }

    print()
    print("summary")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
