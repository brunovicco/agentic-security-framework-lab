# LangGraph LiteLLM Gateway Smoke

## Purpose

This increment validates the first framework migration through the centralized LiteLLM Proxy without creating a new benchmark baseline.

The target path is:

```text
canonical evaluation scenario
        |
        v
LangGraph evaluator-optimizer
        |
        v
LangChain ChatOpenAI
        |
        | model = security-analysis
        v
LiteLLM Proxy
        |
        v
configured upstream provider model
```

The domain model, evidence contract, expected truth, deterministic evaluator, retry semantics, oracle fallback, and final result construction remain unchanged.

## Documentation freshness check

Checked on 2026-09-04 against the current LiteLLM Getting Started guidance and the current official LiteLLM Helm configuration.

The official guidance continues to describe the Proxy Server as a central LLM Gateway and demonstrates OpenAI-compatible clients using a proxy `base_url` plus a model name configured on the gateway.

The current LiteLLM Helm configuration uses `GET /health/readiness` for readiness and `GET /health/liveliness` for liveness. The smoke now waits for the readiness endpoint before starting LangGraph execution.

That is the pattern used by this lab. The application does not embed the LiteLLM Python SDK.

## Why this is a smoke, not a benchmark

The existing framework benchmark is historical evidence collected before the gateway migration. Re-running the same sample through a new network boundary changes the experiment.

The gateway smoke therefore uses:

- the five canonical framework-neutral scenarios;
- exactly one execution per scenario;
- the same LangGraph evaluator-optimizer path;
- the same deterministic expected truth;
- a separate `artifacts/gateway-smoke/langgraph/` namespace;
- `official_baseline: false`;
- `review_status: pending_manual_trace_review`.

Five runs are enough to test contract compatibility across the canonical scenario shapes without pretending to provide a latency distribution or framework ranking.

## Readiness preflight

A background proxy process is not necessarily ready to accept requests immediately after the shell returns a PID. Starting the smoke without a readiness check can therefore produce a misleading `Connection refused` error before the first scenario reaches the gateway.

Before constructing the LangGraph workload, the smoke now:

1. requires the configured gateway base URL and client credential;
2. requests the LiteLLM `GET /health/readiness` endpoint;
3. retries connection-level failures for a short bounded window;
4. starts the canonical scenarios only after HTTP 200;
5. fails with a startup-specific diagnostic if readiness is never reached.

The credential is used only in the readiness request and the normal OpenAI-compatible client path. It is never written to the smoke artifact.

This readiness loop is orchestration hygiene, not an application-level LLM retry policy. Provider retries and gateway fallback policies remain separate experiments.

## Fail-closed acceptance criteria

Every smoke run must have:

1. a final asset classification matching the external expected truth;
2. deterministic validation passing;
3. at least one recorded model call;
4. non-zero standardized token usage metadata.

Any violation makes the smoke assessment fail.

The model-call and token requirements matter because a correct deterministic fallback by itself would not prove that the new provider-access path actually exercised the gateway successfully.

## Configuration evidence vs runtime evidence

The smoke artifact records two model identities:

```text
model_alias = security-analysis
configured_upstream_model = <value from config/litellm/config.yaml>
```

The first is the client contract. The second is read from the committed gateway configuration.

The configured upstream value must be interpreted as **configuration evidence**, not independent provider-response attestation. The current LangChain analyzer intentionally returns the application draft rather than leaking raw provider response metadata into application contracts.

This distinction avoids overstating what the smoke proves.

## Secret and infrastructure hygiene

The artifact never persists:

- `AGENTIC_LAB_GATEWAY_API_KEY`;
- `LITELLM_MASTER_KEY`;
- `OPENAI_API_KEY`;
- the gateway endpoint URL.

Only the fact that an OpenAI-compatible gateway transport was used is recorded.

## Run locally

Start the pinned proxy after loading the provider and gateway secrets:

```bash
uv tool install 'litellm[proxy]==1.98.0'
litellm --config config/litellm/config.yaml \
  > /tmp/agentic-lab-litellm.log 2>&1 &
export LITELLM_PID=$!
```

Configure the migrated LangGraph client and run the smoke:

```bash
export AGENTIC_LAB_GATEWAY_BASE_URL="http://localhost:4000"
export AGENTIC_LAB_GATEWAY_API_KEY="$LITELLM_MASTER_KEY"

uv run python scripts/smoke_langgraph_gateway.py
```

The runner waits for LiteLLM readiness before it executes any model-backed scenario. If readiness fails, inspect:

```bash
ps -p "$LITELLM_PID"
tail -n 100 /tmp/agentic-lab-litellm.log
```

Successful execution writes:

```text
artifacts/gateway-smoke/langgraph/latest.json
artifacts/gateway-smoke/langgraph/latest.md
```

## Manual review before acceptance

After execution, review all five runs before treating the smoke as accepted evidence. Check:

- scenario identity;
- expected truth match;
- validation status;
- analysis source;
- retry count;
- model-call count;
- token accounting;
- whether any deterministic fallback occurred unexpectedly.

Do not compare gateway smoke latency directly with the historical framework benchmark. The additional proxy hop changes the runtime topology and the smoke has only one execution per scenario.

## What this increment does not test

It does not yet test:

- gateway retries or fallbacks;
- multiple providers behind the alias;
- virtual keys;
- budgets or rate limits;
- spend tracking;
- database-backed policy;
- distributed tracing across application, gateway, and provider;
- failure behavior after a ready gateway becomes unavailable.

Those remain separate experiments so each new policy has an explicit hypothesis and acceptance criteria.
