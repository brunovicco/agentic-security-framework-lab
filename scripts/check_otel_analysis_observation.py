"""Validate the safe analysis observation contract with an in-memory OTel exporter."""

import json

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from agentic_lab.observability.analysis import (
    ANALYSIS_SPAN_NAME,
    AnalysisExecutionObservation,
    analysis_span_attributes,
)

_FORBIDDEN_ATTRIBUTE_TERMS = (
    "prompt",
    "evidence",
    "rationale",
    "feedback",
    "credential",
    "secret",
    "token",
    "asset_id",
    "cve_id",
)


def main() -> None:
    """Emit one safe logical-analysis span and fail closed on contract drift."""
    observation = AnalysisExecutionObservation(
        framework="langgraph",
        workflow="langgraph-evaluator-optimizer",
        analysis_source="llm",
        validation_passed=True,
        analysis_attempts=1,
        model_calls=1,
        requires_human_review=True,
    )
    attributes = analysis_span_attributes(observation)

    provider = TracerProvider()
    exporter = InMemorySpanExporter()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    tracer = provider.get_tracer("agentic_security_framework_lab.observability")

    with tracer.start_as_current_span(ANALYSIS_SPAN_NAME, attributes=attributes):
        pass

    spans = exporter.get_finished_spans()
    if len(spans) != 1:
        raise RuntimeError(f"Expected exactly one analysis span, observed {len(spans)}")

    span = spans[0]
    if span.name != ANALYSIS_SPAN_NAME:
        raise RuntimeError(f"Unexpected analysis span name: {span.name!r}")
    observed_attributes = dict(span.attributes or {})
    if observed_attributes != attributes:
        raise RuntimeError("Exported analysis span attributes differ from the safe contract")

    attribute_keys = tuple(observed_attributes)
    unsafe_keys = sorted(
        key
        for key in attribute_keys
        if any(term in key.lower() for term in _FORBIDDEN_ATTRIBUTE_TERMS)
    )
    if unsafe_keys:
        raise RuntimeError(f"Unsafe content-bearing telemetry keys detected: {unsafe_keys}")

    print(
        json.dumps(
            {
                "type": "otel_analysis_observation_check",
                "span_name": span.name,
                "span_count": len(spans),
                "attribute_count": len(observed_attributes),
                "safe_attribute_contract": True,
            }
        )
    )


if __name__ == "__main__":
    main()
