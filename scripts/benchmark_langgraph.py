"""Benchmark the validated LangGraph vulnerability-analysis workflow."""

import argparse
import json
import math
import os
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
from agentic_lab.adapters.langchain.model import create_chat_model
from agentic_lab.adapters.langgraph.llm_graph import (
    run_llm_analysis_graph,
)

_MODEL_ENV = "AGENTIC_LAB_MODEL"


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


def require_model_name() -> str:
    """Return the configured model name."""
    model_name = os.environ.get(_MODEL_ENV)

    if not model_name:
        raise RuntimeError(f"{_MODEL_ENV} must identify the model used by the benchmark")

    return model_name


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
    model_name = require_model_name()

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

        benchmark_run = BenchmarkRun(
            run=run_number,
            model=model_name,
            latency_ms=round(latency_ms, 2),
            analysis_source=output["analysis_source"],
            validation_passed=output["validation_passed"],
            confidence=result.confidence,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            total_tokens=usage.total_tokens,
        )

        benchmark_runs.append(benchmark_run)

        print(json.dumps(asdict(benchmark_run)))

    accepted = sum(run.analysis_source == "llm" for run in benchmark_runs)
    fallbacks = len(benchmark_runs) - accepted

    latencies = [run.latency_ms for run in benchmark_runs]

    summary = {
        "framework": "langgraph",
        "model": model_name,
        "runs": len(benchmark_runs),
        "accepted": accepted,
        "fallbacks": fallbacks,
        "acceptance_rate": accepted / len(benchmark_runs),
        "fallback_rate": fallbacks / len(benchmark_runs),
        "mean_latency_ms": round(mean(latencies), 2),
        "p50_latency_ms": round(median(latencies), 2),
        "p95_latency_ms": round(
            nearest_rank_percentile(latencies, 0.95),
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
