# LlamaIndex LiteLLM Gateway Smoke

## Purpose

This is a provider-backed compatibility smoke for the LlamaIndex migration to the centralized LiteLLM gateway.

It is **not** an official benchmark and must not be used to compare latency, token efficiency, or framework quality with historical results.

The smoke answers a narrower question:

> Can the migrated LlamaIndex Workflow execute the canonical workload through the governed `security-analysis` alias while preserving external expected truth, deterministic validation, structured prediction, and observable LLM usage?

## Runtime surface

The smoke exercises the native LlamaIndex Workflow path used by the framework benchmark:

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

The runner uses one process-level event loop and calls the async-first Workflow path for each scenario. Each Workflow execution creates an isolated LlamaIndex analysis runner and token counter through the existing runtime factory.

## Evidence boundary

Every run must satisfy all of the following:

1. final asset applicability matches the framework-neutral expected truth;
2. deterministic validation accepts the LLM draft;
3. the final analysis source is `llm`, not deterministic fallback;
4. at least one analysis attempt occurred;
5. at least one model call was reported;
6. reported model calls are not fewer than application analysis attempts;
7. prompt, completion, and total token usage are all greater than zero.

A correct final answer produced by deterministic fallback is therefore a smoke failure. The purpose is to prove that the migrated LlamaIndex-to-LiteLLM path itself executed successfully, not merely that the overall system remained safe.

The persisted artifact records the committed upstream model mapping as **configuration evidence**. It is not independent provider-response attestation.

The artifact never persists:

- `AGENTIC_LAB_GATEWAY_API_KEY`;
- `LITELLM_MASTER_KEY`;
- `OPENAI_API_KEY`;
- the gateway endpoint URL.

The smoke does not require `AGENTIC_LAB_MODEL`. The transitional `model_name` constructor input is populated with the governed gateway alias and does not select provider access. Issue #55 tracks removal of that historical metadata contract only after this provider-backed smoke is accepted.

## LlamaIndex usage semantics

`LlamaIndexWorkflowRuntime.arun()` creates a fresh `LlamaIndexRuntime` for each Workflow execution. The runtime owns a `TokenCountingHandler`, and `consume_usage()` returns prompt, completion, total token counts, and the number of observed LLM callback events for that execution.

The smoke therefore treats positive request/token telemetry as part of compatibility evidence rather than relying only on the final system result.

If provider-backed execution reveals different telemetry semantics for the pinned LlamaIndex version, treat the observation as runtime evidence and diagnose it before changing acceptance criteria.

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

Configure provider and gateway secrets without printing them:

```bash
read -s "OPENAI_API_KEY?OpenAI API key: "
echo
export OPENAI_API_KEY

export LITELLM_MASTER_KEY="sk-local-$(openssl rand -hex 24)"
```

Install and start the pinned gateway tool if needed:

```bash
uv tool install 'litellm[proxy]==1.98.0'

: > /tmp/agentic-lab-litellm.log
litellm --config config/litellm/config.yaml \
  > /tmp/agentic-lab-litellm.log 2>&1 &
export LITELLM_PID=$!
```

Configure the client boundary:

```bash
export AGENTIC_LAB_GATEWAY_BASE_URL="http://localhost:4000"
export AGENTIC_LAB_GATEWAY_API_KEY="$LITELLM_MASTER_KEY"
unset AGENTIC_LAB_MODEL
```

Run the LlamaIndex smoke:

```bash
uv run python scripts/smoke_llamaindex_gateway.py
```

A successful execution prints five `gateway_smoke_run` records and finishes with:

```text
{"type": "gateway_smoke_assessment", "passed": true, "runs": 5, "failures": []}
```

It writes reviewable, non-baseline evidence to:

```text
artifacts/gateway-smoke/llamaindex/latest.json
artifacts/gateway-smoke/llamaindex/latest.md
```

## Failure investigation

If readiness fails:

```bash
ps -p "$LITELLM_PID"
tail -n 150 /tmp/agentic-lab-litellm.log
```

If readiness succeeds but a LlamaIndex call fails, capture the exception and final proxy-log lines. Do not paste API keys or gateway credentials.

A failure after readiness should be treated as runtime compatibility evidence. Do not add retries, fallbacks, alternate providers, or gateway policy merely to make the smoke pass; diagnose the failed boundary first.

## Review status

Successful generated artifacts start with:

```text
review_status = pending_manual_trace_review
official_baseline = false
```

Provider-backed execution is necessary but not sufficient for acceptance. Generated evidence must be reviewed before any result is committed as accepted compatibility evidence or before Issue #55 is closed.
