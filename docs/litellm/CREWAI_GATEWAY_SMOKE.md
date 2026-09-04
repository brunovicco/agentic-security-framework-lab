# CrewAI LiteLLM Gateway Smoke

## Purpose

This is a provider-backed compatibility smoke for the CrewAI migration to the centralized LiteLLM gateway.

It is **not** an official benchmark and must not be used to compare latency, token efficiency, or framework quality with historical results.

The smoke answers a narrower question:

> Can both migrated CrewAI integration surfaces execute the canonical workload through the governed `security-analysis` alias while preserving external expected truth, deterministic validation, and observable LLM usage?

## Runtime surfaces

The smoke exercises two CrewAI paths separately:

```text
CrewAI Agent + Task + Crew
    -> application-owned evaluator / retry / fallback
    -> CrewAI LLM(custom OpenAI-compatible endpoint)
    -> security-analysis
    -> LiteLLM Proxy
    -> configured upstream provider
```

and:

```text
CrewAI Flow
    -> direct LLM.call(..., response_model=LLMAnalysisDraft)
    -> deterministic Flow evaluator / retry / fallback
    -> CrewAI LLM(custom OpenAI-compatible endpoint)
    -> security-analysis
    -> LiteLLM Proxy
    -> configured upstream provider
```

The same five framework-neutral canonical scenarios are executed once through each runtime, for ten total executions.

## Evidence boundary

Every run must satisfy all of the following:

1. final asset applicability matches the framework-neutral expected truth;
2. deterministic validation accepts the LLM draft;
3. the final analysis source is `llm`, not deterministic fallback;
4. at least one analysis attempt occurred;
5. at least one model call was reported;
6. reported model calls are not fewer than application analysis attempts;
7. total token usage is greater than zero.

A correct final answer produced by deterministic fallback is therefore a smoke failure. The purpose is to prove that the migrated CrewAI-to-LiteLLM path itself executed successfully, not merely that the overall system remained safe.

The persisted artifact records the committed upstream model mapping as **configuration evidence**. It is not independent provider-response attestation.

The artifact never persists:

- `AGENTIC_LAB_GATEWAY_API_KEY`;
- `LITELLM_MASTER_KEY`;
- `OPENAI_API_KEY`;
- the gateway endpoint URL.

The smoke does not require `AGENTIC_LAB_MODEL`. CrewAI receives the governed `security-analysis` alias from the shared gateway client configuration.

## CrewAI usage semantics

The first provider-backed CrewAI gateway execution on 2026-09-04 established an important runtime behavior for the pinned CrewAI 1.15.18 integration: `CrewOutput.token_usage` behaved as a **cumulative snapshot across successive Crew kickoffs in the same process**.

The observed Agent/Crew smoke sequence reported model-call snapshots `1, 2, 3, 4, 5` even though every canonical scenario completed with one application analysis attempt. Token counters increased in the same cumulative shape. That first generated artifact was therefore treated as diagnostic evidence only and must not be persisted as accepted smoke evidence.

`CrewAIRuntime` stores the latest cumulative snapshot and `consume_usage()` calculates the delta from the previously consumed snapshot. This produces per-scenario usage while still allowing multiple model calls inside one application analysis execution to be observed correctly.

`Flow.usage_metrics` is consumed directly from each Flow execution. The provider-backed run observed one model call per canonical Flow scenario.

This runtime observation takes precedence over assumptions derived from documentation when interpreting the pinned version's telemetry behavior.

## Gateway readiness

A background process ID is not proof that the LiteLLM service is ready to accept traffic.

Before the first CrewAI execution, the runner polls:

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

Run the CrewAI smoke:

```bash
uv run python scripts/smoke_crewai_gateway.py
```

The runner disables optional CrewAI tracing for this controlled headless execution.

A successful execution prints ten `gateway_smoke_run` records and finishes with:

```text
{"type": "gateway_smoke_assessment", "passed": true, "runs": 10, "failures": []}
```

It writes reviewable, non-baseline evidence to:

```text
artifacts/gateway-smoke/crewai/latest.json
artifacts/gateway-smoke/crewai/latest.md
```

## Failure investigation

If readiness fails:

```bash
ps -p "$LITELLM_PID"
tail -n 150 /tmp/agentic-lab-litellm.log
```

If readiness succeeds but a CrewAI call fails, capture the exception, final proxy-log lines, and which runtime was executing. Do not paste API keys or gateway credentials.

A failure after readiness should be treated as runtime compatibility evidence. Do not add retries, fallbacks, alternate providers, or gateway policy merely to make the smoke pass; diagnose the failed boundary first.

## Review status

Successful generated artifacts start with:

```text
review_status = pending_manual_trace_review
official_baseline = false
```

Provider-backed execution is necessary but not sufficient for promotion. Generated evidence must be reviewed before any result is committed as accepted compatibility evidence.
