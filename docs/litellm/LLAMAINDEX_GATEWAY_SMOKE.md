# LlamaIndex LiteLLM Gateway Smoke

## Purpose

This is a provider-backed compatibility smoke for the LlamaIndex migration to the centralized LiteLLM gateway.

It is **not** an official benchmark and must not be used to compare latency, token efficiency, or framework quality with historical results.

The smoke exercises the native LlamaIndex Workflow path:

```text
LlamaIndex Workflow
    -> LlamaIndex `structured_predict()`
    -> typed OpenAI-compatible transport
    -> security-analysis
    -> LiteLLM Proxy
    -> configured upstream provider
    -> deterministic evaluator / bounded retry / fallback
```

The same five framework-neutral canonical scenarios are executed exactly once.

## Evidence model

The smoke records four related assessments rather than collapsing different questions into one result.

### Transport compatibility

`transport_compatibility` asks whether the migrated framework path actually exercised the gateway-backed provider boundary with observable telemetry.

It requires:

1. the complete canonical scenario set;
2. at least one analysis attempt per run;
3. at least one observed model call per run;
4. `model_calls >= analysis_attempts`;
5. positive prompt, completion, and total token usage.

This dimension does **not** claim that the LLM produced the correct semantic answer.

### Semantic quality

`semantic_quality` asks whether probabilistic LLM reasoning itself satisfied the shared deterministic evaluator.

It requires for every run:

1. deterministic validation passes;
2. final `analysis_source` is `llm`, not deterministic oracle fallback.

A correct final answer rescued by fallback is therefore a semantic-quality failure. The repository continues to preserve the principle:

> correct final system result != LLM succeeded

### System safety

`system_safety` asks whether the final governed result matches framework-neutral external expected truth.

A run can therefore have:

```text
transport_compatibility = PASS
semantic_quality = FAIL
system_safety = PASS
```

when the provider path works, probabilistic reasoning exhausts bounded retries, and deterministic fallback preserves the correct final result.

### Overall gate

`overall` remains fail closed and passes only when all three evidence dimensions pass.

The smoke command therefore continues to exit non-zero when semantic quality fails. Splitting the evidence model does not weaken the existing process gate; it prevents a semantic model failure from being misreported as a gateway transport failure.

## Why the dimensions are separate

Provider-backed investigation of the canonical `product-mismatch` scenario showed reproducible model-output variability around the distinction between `not_affected` and `not_applicable`.

A controlled matrix produced identical results in isolated and `baseline-mixed -> product-mismatch` modes:

```text
samples per mode:       3
first-attempt accepts:  1
final LLM accepts:      2
oracle fallbacks:       1
```

That evidence does not support sequence/state contamination. It supports separating transport compatibility from probabilistic semantic quality instead of repeating a one-shot smoke until a favorable sample appears.

The smoke itself remains one execution per canonical scenario. It is compatibility evidence, not a statistical model-quality benchmark.

## Evidence boundary

The persisted artifact records the committed upstream model mapping as **configuration evidence**. It is not independent provider-response attestation.

The artifact never persists:

- `AGENTIC_LAB_GATEWAY_API_KEY`;
- `LITELLM_MASTER_KEY`;
- `OPENAI_API_KEY`;
- the gateway endpoint URL;
- prompts, rationales, recommendations, or evaluator feedback text.

The smoke does not require `AGENTIC_LAB_MODEL`. The transitional `model_name` constructor input is populated with the governed gateway alias and does not select provider access. Issue #55 tracks removal of that historical metadata contract after transport compatibility evidence is explicitly reviewed.

## Artifact schema

The split evidence structure is persisted as gateway-smoke schema version `2`.

Generated evidence keeps:

```text
official_baseline = false
review_status = pending_manual_trace_review
```

The JSON artifact contains a top-level `smoke_assessment` with:

```text
passed
runs
failures
transport_compatibility
semantic_quality
system_safety
```

The top-level `passed` value is the fail-closed overall gate.

## LlamaIndex usage semantics

`LlamaIndexWorkflowRuntime.arun()` creates a fresh `LlamaIndexRuntime` for each Workflow execution. The runtime owns a `TokenCountingHandler`, and `consume_usage()` returns prompt, completion, total token counts, and the number of observed LLM callback events for that execution.

Positive request/token telemetry is transport-compatibility evidence rather than proof of semantic correctness.

## Gateway readiness

A background process ID is not proof that the LiteLLM service is ready to accept traffic.

Before the first LlamaIndex execution, the runner polls:

```text
GET /health/readiness
```

The check is bounded and uses the configured gateway client credential. It retries connection-level startup failures, but it does not introduce application-level LLM retry or provider fallback policy.

## Local execution

Update the repository first:

```bash
cd /Users/brunovicco/Projects/agentic-security-framework-lab
git checkout main
git pull --ff-only
```

Configure provider and gateway secrets without printing them, then start the pinned LiteLLM proxy and configure:

```bash
export AGENTIC_LAB_GATEWAY_BASE_URL="http://localhost:4000"
export AGENTIC_LAB_GATEWAY_API_KEY="$LITELLM_MASTER_KEY"
unset AGENTIC_LAB_MODEL
```

Run:

```bash
uv run python scripts/smoke_llamaindex_gateway.py
```

The runner prints five `gateway_smoke_run` records followed by one `gateway_smoke_assessment` containing the overall and dimensional results.

It writes reviewable, non-baseline evidence to:

```text
artifacts/gateway-smoke/llamaindex/latest.json
artifacts/gateway-smoke/llamaindex/latest.md
```

A failed overall run still writes the candidate artifact so the independently valid dimensions can be reviewed. It must not be described as semantic LLM success when `semantic_quality` fails.

## Failure investigation

If readiness fails:

```bash
ps -p "$LITELLM_PID"
tail -n 150 /tmp/agentic-lab-litellm.log
```

If transport compatibility fails after readiness, diagnose the framework/client/proxy/provider boundary before changing acceptance criteria.

If transport compatibility passes but semantic quality fails, treat that as model-quality evidence. Do not add gateway retries, alternate providers, or weaken deterministic validation merely to obtain a passing sample.

If system safety fails, treat it as the highest-priority governed-system failure because the final result no longer matches external expected truth.

## Review status

Provider-backed execution is necessary but not sufficient for acceptance.

Manual review must state exactly which evidence dimensions are accepted. A reviewer may accept transport compatibility while recording semantic-quality variability; that does not convert a fallback-rescued run into LLM success.

Issue #55 may proceed only after transport compatibility is explicitly reviewed. Historical benchmark artifacts remain unchanged.
