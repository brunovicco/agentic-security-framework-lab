# Agno LiteLLM Gateway Smoke

## Purpose

This is a provider-backed compatibility smoke for the Agno migration to the centralized LiteLLM gateway.

It is **not** an official benchmark and must not be used to compare latency, token efficiency, or framework quality with historical results.

The smoke answers a narrower question:

> Can the migrated Agno Workflow execute the canonical workload through the governed `security-analysis` alias with observable model usage while keeping model quality and final system safety independently reviewable?

## Runtime surface

The smoke exercises the native Agno Workflow path used by the framework benchmark:

```text
Agno Workflow
    -> Agno Agent
    -> OpenAILike
    -> security-analysis
    -> LiteLLM Proxy
    -> configured upstream provider
    -> deterministic evaluator / bounded retry / fallback
```

The same five framework-neutral canonical scenarios are executed exactly once.

The smoke passes the governed alias into the existing Agno Workflow runtime as transitional metadata. The actual model client does not select a direct provider model from that input: `OpenAILike` resolves `security-analysis`, the gateway base URL, and the gateway client credential from the shared gateway boundary.

## Evidence dimensions

The schema-v2 smoke records three independent dimensions.

### Transport compatibility

Every run must have:

- at least one analysis attempt;
- at least one model call;
- model-call telemetry not lower than application analysis attempts;
- positive input, output, and total token usage;
- the complete five-scenario set.

This is the evidence that the model path actually executed. It does not claim that the LLM answer was semantically correct.

### Semantic quality

Every run must have:

- deterministic validation accepted;
- final `analysis_source = llm`.

A correct result produced by oracle fallback therefore fails semantic quality.

### System safety

Every final result must match the framework-neutral expected asset applicability.

A fallback may preserve this dimension even when semantic quality fails. That distinction is intentional: a safe governed result is not the same thing as successful LLM reasoning.

### Overall gate

The command remains fail-closed. `passed=true` requires all three dimensions to pass.

The split makes failure interpretable; it does not weaken the acceptance gate.

## Gateway readiness

Before the first Agno execution, the runner polls:

```text
GET /health/readiness
```

The check is bounded and authenticates with the gateway client credential. A running process ID is not considered readiness evidence.

## Artifact boundary

Generated evidence is written to:

```text
artifacts/gateway-smoke/agno/latest.json
artifacts/gateway-smoke/agno/latest.md
```

The artifact uses:

```text
schema_version = 2
artifact_type = gateway_smoke
official_baseline = false
review_status = pending_manual_trace_review
```

The committed upstream model mapping is recorded as **configuration evidence**, not independent provider-response attestation.

The artifact never persists:

- `AGENTIC_LAB_GATEWAY_API_KEY`;
- `LITELLM_MASTER_KEY`;
- `OPENAI_API_KEY`;
- the gateway endpoint URL;
- prompts, rationales, or evaluator feedback text.

## Local execution

Update the repository first:

```bash
cd /Users/brunovicco/Projects/agentic-security-framework-lab
git checkout main
git pull --ff-only
```

The gateway service and client boundary require the same environment used by the accepted LangGraph, CrewAI, and LlamaIndex smokes:

```text
OPENAI_API_KEY
LITELLM_MASTER_KEY
AGENTIC_LAB_GATEWAY_BASE_URL
AGENTIC_LAB_GATEWAY_API_KEY
```

The dedicated Agno smoke does **not** require `AGENTIC_LAB_MODEL`.

Run:

```bash
uv run python scripts/smoke_agno_gateway.py
```

A successful execution prints five `gateway_smoke_run` records and finishes with a schema-v2 `gateway_smoke_assessment` where transport compatibility, semantic quality, system safety, and overall are all true.

## Review status

Provider-backed execution is necessary but not sufficient for acceptance. The generated artifact must be persisted exactly and reviewed in a separate increment before transitional Agno direct-model metadata contracts are removed.

Do not repeat the smoke until a favorable run appears and selectively persist that sample. If semantic quality varies, preserve that observation and distinguish it from transport compatibility and system safety.
