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

Documentation was rechecked on 2026-09-04 before adding this smoke.

CrewAI usage metrics aggregate model calls within one execution boundary. `Flow.usage_metrics` aggregates calls made during one Flow kickoff and resets for the next kickoff. A `CrewOutput.token_usage` observation belongs to that Crew execution rather than acting as a process-wide cumulative counter across independent Crew kickoffs.

Because the application-owned evaluator may invoke the Agent/Crew path more than once, `CrewAIRuntime` accumulates each kickoff's usage before `consume_usage()` calculates the benchmark/smoke delta. This prevents retries from being under-counted or interpreted as decreasing cumulative counters.

Flow already exposes one aggregated usage observation for each `flow.kickoff()` through `flow.usage_metrics`.

## Gateway readiness

A background process ID is not proof that the LiteLLM service is ready to accept traffic.

Before the first CrewAI execution, the runner polls the LiteLLM readiness endpoint:

```text
GET /health/readiness
```

The check is bounded and uses the configured gateway client credential. It retries connection-level startup failures such as `ConnectionRefusedError`, but it does not introduce an application-level LLM retry or provider fallback policy.

If readiness never succeeds, the smoke fails before running the CrewAI workload and directs the operator to inspect the proxy process and startup log.

## Local execution

Update the repository first:

```bash
cd /Users/brunovicco/Projects/agentic-security-framework-lab
git checkout main
git pull --ff-only
```

Configure the provider and gateway secrets without printing them:

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
```

Run the CrewAI smoke:

```bash
uv run python scripts/smoke_crewai_gateway.py
```

The runner disables optional CrewAI tracing for this controlled headless execution.

A successful execution prints ten records shaped like:

```text
{"type": "gateway_smoke_run", "runtime": "agent_crew", ...}
{"type": "gateway_smoke_run", "runtime": "flow", ...}
```

and finishes with:

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

If readiness succeeds but a CrewAI call fails, capture:

- the exception and stack trace from `smoke_crewai_gateway.py`;
- the corresponding final lines of `/tmp/agentic-lab-litellm.log`;
- which runtime was executing (`agent_crew` or `flow`).

Do not paste API keys or gateway credentials.

A failure after readiness should be treated as runtime compatibility evidence. It may indicate a structured-output, OpenAI-compatible transport, provider-access, or CrewAI-specific behavior issue. Do not add retries, fallbacks, alternate providers, or gateway policy merely to make the smoke pass; diagnose the failed boundary first.

## Review status

Successful generated artifacts start with:

```text
review_status = pending_manual_trace_review
official_baseline = false
```

Provider-backed execution is necessary but not sufficient for promotion. The generated evidence must be reviewed before any result is committed as accepted compatibility evidence.
