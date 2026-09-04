"""Run LangGraph against the adversarial v2 evidence-plane dataset."""

import argparse
import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import cast

from langchain_core.callbacks import get_usage_metadata_callback
from langchain_core.messages import UsageMetadata

from agentic_lab.adapters.fixtures.adversarial_v2_evidence import (
    load_adversarial_v2_evidence_scenarios,
)
from agentic_lab.adapters.langchain.analyzer import LangChainVulnerabilityAnalyzer
from agentic_lab.adapters.langchain.model import create_chat_model, gateway_model_alias
from agentic_lab.adapters.langgraph.llm_graph import run_llm_analysis_graph_with_evidence
from agentic_lab.adapters.langgraph.state import LLMAnalysisGraphOutput
from agentic_lab.application.adversarial_reporting import (
    AdversarialRun,
    AdversarialRuntimeUsage,
    OverallSummary,
    ScenarioSummary,
    build_adversarial_run,
    render_adversarial_markdown_report,
    summarize_runs,
)
from agentic_lab.application.adversarial_v2 import (
    AdversarialEvidenceScenario,
    build_adversarial_v2_evidence_bundle,
)
from agentic_lab.application.evidence_document_analyzer import bind_evidence_documents
from agentic_lab.application.validated_analysis import ValidatedAnalysisOutput

_FRAMEWORK = "langgraph"
_PATTERN = "evaluator_optimizer_adversarial_v2_evidence_plane"
_SAMPLING = "provider_default"
_OUTPUT_DIR = Path("artifacts/adversarial-v2/langgraph")


@dataclass(frozen=True, slots=True)
class TokenCounts:
    """Represent token counts reported by LangChain callbacks."""

    input_tokens: int
    output_tokens: int
    total_tokens: int


def parse_runs() -> int:
    """Parse repetitions per adversarial v2 scenario."""
    parser = argparse.ArgumentParser(
        description="Run LangGraph against the adversarial v2 evidence-plane dataset.",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=1,
        help="Number of executions per adversarial v2 scenario.",
    )
    args = parser.parse_args()
    runs = cast(int, args.runs)

    if runs < 1:
        raise ValueError("--runs must be at least 1")

    return runs


def aggregate_usage(usage_by_model: Mapping[str, UsageMetadata]) -> TokenCounts:
    """Aggregate standardized LangChain token usage."""
    return TokenCounts(
        input_tokens=sum(usage["input_tokens"] for usage in usage_by_model.values()),
        output_tokens=sum(usage["output_tokens"] for usage in usage_by_model.values()),
        total_tokens=sum(usage["total_tokens"] for usage in usage_by_model.values()),
    )


def build_validated_output(output: LLMAnalysisGraphOutput) -> ValidatedAnalysisOutput:
    """Adapt LangGraph output to the framework-neutral adversarial evaluator."""
    return ValidatedAnalysisOutput(
        result=output["result"],
        analysis_source=output["analysis_source"],
        validation_passed=output["validation_passed"],
        validation_reason=output["validation_reason"],
        analysis_attempts=output["analysis_attempts"],
        attempt_trace=output["attempt_trace"],
    )


def build_run(
    scenario: AdversarialEvidenceScenario,
    iteration: int,
    model_name: str,
    latency_ms: float,
    output: LLMAnalysisGraphOutput,
    token_counts: TokenCounts,
) -> AdversarialRun:
    """Build one fully evaluated adversarial v2 run."""
    validated_output = build_validated_output(output)
    usage = AdversarialRuntimeUsage(
        model_calls=validated_output.analysis_attempts,
        input_tokens=token_counts.input_tokens,
        output_tokens=token_counts.output_tokens,
        total_tokens=token_counts.total_tokens,
    )
    return build_adversarial_run(
        scenario=scenario,
        iteration=iteration,
        model_name=model_name,
        latency_ms=latency_ms,
        output=validated_output,
        usage=usage,
    )


def write_artifacts(
    model_name: str,
    repetitions: int,
    runs: list[AdversarialRun],
    scenario_summaries: list[ScenarioSummary],
    overall: OverallSummary,
) -> None:
    """Persist machine-readable and human-readable v2 adversarial artifacts."""
    generated_at = datetime.now(UTC).isoformat()
    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    payload = {
        "schema_version": "1",
        "suite_version": "2",
        "generated_at_utc": generated_at,
        "framework": _FRAMEWORK,
        "pattern": _PATTERN,
        "model": model_name,
        "sampling": _SAMPLING,
        "repetitions_per_scenario": repetitions,
        "scenario_count": len(scenario_summaries),
        "runs": [asdict(run) for run in runs],
        "scenario_summaries": [asdict(summary) for summary in scenario_summaries],
        "overall_summary": asdict(overall),
    }

    json_path = _OUTPUT_DIR / "latest.json"
    markdown_path = _OUTPUT_DIR / "latest.md"
    json_path.write_text(json.dumps(payload, indent=2) + "\n")
    markdown_path.write_text(
        render_adversarial_markdown_report(
            title="LangGraph Adversarial Security Evaluation v2",
            generated_at_utc=generated_at,
            model_name=model_name,
            framework=_FRAMEWORK,
            pattern=_PATTERN,
            scenario_summaries=scenario_summaries,
            overall=overall,
        )
    )

    print()
    print(f"artifact_json: {json_path}")
    print(f"artifact_markdown: {markdown_path}")


def main() -> None:
    """Execute the dedicated LangGraph adversarial v2 evaluation."""
    repetitions = parse_runs()
    model_name = gateway_model_alias()
    scenarios = load_adversarial_v2_evidence_scenarios()
    model = create_chat_model()
    document_analyzer = LangChainVulnerabilityAnalyzer(model)

    all_runs: list[AdversarialRun] = []
    scenario_summaries: list[ScenarioSummary] = []

    for scenario in scenarios:
        evidence_bundle = build_adversarial_v2_evidence_bundle(scenario)
        analyzer = bind_evidence_documents(document_analyzer, evidence_bundle)
        scenario_runs: list[AdversarialRun] = []

        for iteration in range(1, repetitions + 1):
            started_at = perf_counter()

            with get_usage_metadata_callback() as usage_callback:
                output = run_llm_analysis_graph_with_evidence(
                    analyzer=analyzer,
                    evidence_bundle=evidence_bundle,
                )

            latency_ms = (perf_counter() - started_at) * 1000
            token_counts = aggregate_usage(usage_callback.usage_metadata)
            run = build_run(
                scenario=scenario,
                iteration=iteration,
                model_name=model_name,
                latency_ms=latency_ms,
                output=output,
                token_counts=token_counts,
            )
            scenario_runs.append(run)
            all_runs.append(run)
            print(json.dumps({"type": "run", **asdict(run)}))

        summary = ScenarioSummary(
            scenario_id=scenario.scenario_id,
            attack_class=scenario.attack_class,
            tags=scenario.tags,
            metrics=summarize_runs(scenario_runs),
        )
        scenario_summaries.append(summary)
        print(json.dumps({"type": "scenario_summary", **asdict(summary)}))

    overall = OverallSummary(
        framework=_FRAMEWORK,
        pattern=_PATTERN,
        model=model_name,
        scenarios=len(scenarios),
        metrics=summarize_runs(all_runs),
    )

    print()
    print("overall_summary")
    print(json.dumps(asdict(overall), indent=2))
    write_artifacts(
        model_name=model_name,
        repetitions=repetitions,
        runs=all_runs,
        scenario_summaries=scenario_summaries,
        overall=overall,
    )


if __name__ == "__main__":
    main()
