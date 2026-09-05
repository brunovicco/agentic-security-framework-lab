# ADR 0004: Establish an application-owned observability contract before framework telemetry

- Status: Accepted
- Date: 2026-09-04

## Context

The lab now executes the same security-sensitive workload through LangGraph, CrewAI, LlamaIndex, and Agno, with provider access centralized behind LiteLLM and a local MCP v2 capability boundary.

Each framework and provider can expose its own tracing or telemetry integrations. Enabling those independently would make the first observability dataset framework-specific and could also capture prompts, retrieved evidence, rationales, evaluator feedback, or provider details before the project has defined a data-minimization policy.

The comparison goal requires a stable logical execution view above framework-specific implementation details.

OpenTelemetry's current Python guidance supports manual instrumentation for meaningful application operations. OpenTelemetry also recommends low-cardinality span names and selective attributes. GenAI semantic conventions continue to evolve, and content-bearing GenAI attributes may contain sensitive information.

## Decision

Define a small framework-neutral observation contract for one logical validated-analysis execution before instrumenting individual framework/provider internals.

The first logical span is named:

```text
validated_analysis
```

Its allowed attributes are intentionally limited to:

```text
agentic.security.framework
agentic.security.workflow
agentic.security.analysis.source
agentic.security.validation.passed
agentic.security.analysis.attempts
agentic.security.model.calls
agentic.security.human_review.required
```

The contract contains operational facts already produced by the controlled workload. It does not contain the analyzed vulnerability or asset data itself.

The foundation keeps OpenTelemetry out of the domain and application packages. `agentic_lab.observability` defines only plain Python contracts. An isolated CI check maps that contract to OpenTelemetry SDK spans with an in-memory exporter. Runtime SDK/exporter wiring will be introduced separately.

## Data-minimization rule

The following are excluded from the foundation span contract:

- prompts or system instructions;
- evidence documents or retrieved content;
- LLM rationale or recommendation text;
- evaluator feedback text;
- asset identifiers;
- CVE identifiers;
- credentials, keys, authorization headers, or tokens;
- provider response bodies;
- model input/output message content.

A future requirement to capture any content-bearing field requires a separate decision covering sensitivity, redaction, access control, retention, and opt-in behavior.

## Why not start with framework-native tracing

Framework-native traces are useful for debugging implementation details but do not provide a stable cross-framework semantic layer by themselves.

If one framework records graph nodes, another records crews/tasks, and another records workflow steps, comparing those raw traces can confuse framework structure with workload semantics. The project-owned logical span gives every implementation a common parent operation before framework-specific child spans are considered.

Framework/provider telemetry may be added later as child detail, but it must not become the source of truth for deterministic validation, retry, fallback, or policy outcomes.

## Why not adopt every GenAI semantic convention immediately

The project should use stable semantic conventions where they accurately describe the operation. However, the current GenAI conventions have moved to their own repository and include developing areas. The lab will not claim stable GenAI semantics for custom attributes that represent its own deterministic control loop.

Custom `agentic.security.*` attributes are therefore explicit project vocabulary. If a stable OpenTelemetry convention later covers the same concept, migration should be deliberate and tested rather than silently renaming historical telemetry.

## Consequences

Advantages:

- comparable logical traces across frameworks;
- explicit privacy/data-minimization boundary;
- no dependency from domain/application code to OpenTelemetry;
- exporter choice remains deployment-owned;
- framework telemetry can be layered beneath a stable project semantic operation.

Costs:

- the first span is intentionally coarse;
- framework step timings are not captured yet;
- provider call spans and token semantic conventions remain separate work;
- runtime wiring still needs to be implemented across the workflow adapters.

## Verification strategy

The foundation is verified in two layers:

1. normal unit tests validate observation invariants and the exact safe attribute allowlist without OpenTelemetry;
2. an isolated OpenTelemetry SDK check uses an in-memory exporter to prove one observation becomes one low-cardinality span with only those attributes.

No network exporter is required for this stage.

## References checked

- OpenTelemetry Python manual instrumentation: https://opentelemetry.io/docs/languages/python/instrumentation/
- OpenTelemetry semantic conventions: https://opentelemetry.io/docs/specs/semconv/
- OpenTelemetry semantic-convention authoring guidance: https://opentelemetry.io/docs/specs/semconv/how-to-write-conventions/
- OpenTelemetry GenAI semantic-convention move notice: https://opentelemetry.io/docs/specs/semconv/gen-ai/
