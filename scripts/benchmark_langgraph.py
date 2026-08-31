"""Benchmark the validated LangGraph vulnerability-analysis workflow."""

import argparse
import json
import os
from dataclasses import asdict, dataclass
from statistics import mean
from time import perf_counter
from typing import Literal

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
class BenchmarkRun:
    """Capture measurements for one LangGraph execution."""

    run: int
    model: str
    latency_ms: float
    analysis_source: Literal["llm", "oracle_fallback"]
    validation_passed: bool
    confidence: float


def parse_args() -> argparse.Namespace:
    """Parse benchmark command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Benchmark the validated LangGraph workflow.",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=5,
        help="Number of LLM executions to perform.",
    )

    return parser.parse_args()


def require_model_name() -> str:
    """Return the configured model name."""
    model_name = os.environ.get(_MODEL_ENV)

    if not model_name:
        raise RuntimeError(f"{_MODEL_ENV} must identify the model used by the benchmark")

    return model_name


def main() -> None:
    """Run repeated LangGraph analyses and summarize the results."""
    args = parse_args()

    if args.runs < 1:
        raise ValueError("--runs must be at least 1")

    model_name = require_model_name()

    model = create_chat_model()
    analyzer = LangChainVulnerabilityAnalyzer(model)

    runs: list[BenchmarkRun] = []

    for run_number in range(1, args.runs + 1):
        started_at = perf_counter()

        output = run_llm_analysis_graph(
            analyzer=analyzer,
            cve_id=DEMO_CVE_ID,
        )

        latency_ms = (perf_counter() - started_at) * 1000
        result = output["result"]

        run = BenchmarkRun(
            run=run_number,
            model=model_name,
            latency_ms=round(latency_ms, 2),
            analysis_source=output["analysis_source"],
            validation_passed=output["validation_passed"],
            confidence=result.confidence,
        )
        runs.append(run)

        print(json.dumps(asdict(run)))

    accepted = sum(run.analysis_source == "llm" for run in runs)
    fallbacks = len(runs) - accepted

    summary = {
        "model": model_name,
        "runs": len(runs),
        "accepted": accepted,
        "fallbacks": fallbacks,
        "acceptance_rate": accepted / len(runs),
        "fallback_rate": fallbacks / len(runs),
        "mean_latency_ms": round(
            mean(run.latency_ms for run in runs),
            2,
        ),
        "mean_confidence": round(
            mean(run.confidence for run in runs),
            4,
        ),
    }

    print()
    print("summary")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
