# ADR 0004: Establish an application-owned observability contract before framework telemetry

- Status: Accepted
- Date: 2026-09-04
- Phase 14 milestone: Completed 2026-09-05

## Context

The lab executes the same security-sensitive workload through LangGraph, CrewAI, LlamaIndex, and Agno, with provider access centralized behind LiteLLM and a local MCP v2 capability boundary.

Each framework and provider can expose its own tracing or telemetry integrations. Enabling those independently would make the first observability dataset framework-specific and could also capture prompts, retrieved evidence, rationales, evaluator feedback, or provider details before the project has defined a data-minimization policy.

The comparison goal requires a stable logical execution view above framework-specific implementation details.

OpenTelemetry's current Python guidance supports manual instrumentation for meaningful application operations. OpenTelemetry also recommends low-cardinality span names and selective attributes. GenAI semantic conventions continue to evolve, and content-bearing GenAI attributes may contain sensitive information.

## Decision

Define a small framework-neutral observation contract for one logical validated-analysis execution before instrumenting individual framework/provider internals.

The logical span is named:

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

OpenTelemetry remains outside the domain and application packages. `agentic_lab.observability` owns the logical observation, observer port, safe attribute mapping, and a tracer-compatible `OpenTelemetryAnalysisObserver`. SDK provider, processor, exporter, and collector configuration remain deployment composition concerns.

## Implemented runtime boundaries

The Phase 14 milestone now emits the same logical observation from every controlled framework surface:

- LangGraph evaluator-optimizer;
- CrewAI Agent/Crew;
- CrewAI Flow;
- LlamaIndex Workflow;
- Agno Workflow.

Each integration emits only after the logical execution has a final validated output and the strongest normalized model-call count available at that framework boundary.

`analysis_attempts` and `model_calls` are deliberately separate concepts. Framework-reported request counts are preserved when available rather than collapsed into evaluator attempts. Failed or incomplete executions do not emit a completed logical observation.

The framework adapters depend only on the project-owned observer port. They do not import the OpenTelemetry SDK or configure exporters.

## OpenTelemetry backend boundary

`OpenTelemetryAnalysisObserver` converts one `AnalysisExecutionObservation` into one `validated_analysis` span using an injected tracer-like object.

The observer does not create a `TracerProvider`, choose a span processor, configure an OTLP endpoint, or instantiate a collector. Those decisions belong to the deployment composition root because they vary by environment and backend.

An isolated CI check installs `opentelemetry-sdk==1.44.0`, creates a real SDK tracer with an in-memory exporter, passes that tracer through `OpenTelemetryAnalysisObserver`, and verifies that exactly one span is exported with exactly the seven allowed attributes.

A network exporter is intentionally not required to prove the application observability contract. Adding an OTLP collector or vendor backend becomes justified when the lab has an actual deployment target or operational requirement, not merely to expand the technology list.

## Data-minimization rule

The following are excluded from the span contract:

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

If one framework records graph nodes, another records crews/tasks, and another records workflow steps, comparing those raw traces can confuse framework structure with workload semantics. The project-owned logical span gives every implementation a common operation before framework-specific child spans are considered.

Framework/provider telemetry may be added later as child detail, but it must not become the source of truth for deterministic validation, retry, fallback, or policy outcomes.

## Why not adopt every GenAI semantic convention immediately

The project should use stable semantic conventions where they accurately describe the operation. However, the current GenAI conventions have moved to their own repository and include developing areas. The lab will not claim stable GenAI semantics for custom attributes that represent its own deterministic control loop.

Custom `agentic.security.*` attributes are therefore explicit project vocabulary. If a stable OpenTelemetry convention later covers the same concept, migration should be deliberate and tested rather than silently renaming historical telemetry.

## Consequences

Advantages:

- comparable logical traces across all controlled framework surfaces;
- explicit privacy/data-minimization boundary;
- no dependency from domain/application/framework adapters to the OpenTelemetry SDK;
- exporter and collector choice remain deployment-owned;
- framework telemetry can be layered beneath a stable project semantic operation;
- framework-specific request-count semantics remain visible instead of being normalized inaccurately.

Costs and deliberate limits:

- the logical span is intentionally coarse;
- framework step timings are not captured;
- provider transport spans and token semantic conventions remain separate concerns;
- there is no network collector or production telemetry backend in the lab milestone;
- deployment code must provide a configured tracer when external export is required.

## Verification strategy

The completed milestone is verified in three layers:

1. unit tests validate observation invariants and the exact safe attribute allowlist without OpenTelemetry;
2. provider-free framework tests prove each runtime emits exactly one final logical observation across first-pass, retry, fallback, incomplete-telemetry, and failure paths relevant to that framework;
3. an isolated OpenTelemetry SDK 1.44.0 check uses a real tracer and in-memory exporter to prove `OpenTelemetryAnalysisObserver` emits one low-cardinality span with only the seven allowed attributes.

MCP v2 compatibility and real STDIO Host/Client checks remain part of the same project quality workflow, protecting the previous phase while observability evolves.

## References checked

- OpenTelemetry Python manual instrumentation: https://opentelemetry.io/docs/languages/python/instrumentation/
- OpenTelemetry semantic conventions: https://opentelemetry.io/docs/specs/semconv/
- OpenTelemetry semantic-convention authoring guidance: https://opentelemetry.io/docs/specs/semconv/how-to-write-conventions/
- OpenTelemetry GenAI semantic-convention move notice: https://opentelemetry.io/docs/specs/semconv/gen-ai/
