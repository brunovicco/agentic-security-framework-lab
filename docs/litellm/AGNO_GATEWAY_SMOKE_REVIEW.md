# Agno LiteLLM Gateway Smoke Review

Review decision: **accepted_manual_trace_review**

Reviewed at: `2026-09-04T22:32:14+00:00`

Reviewed against repository commit: `91d2702588330efbca8272ad7cc104487fafb108`

Source artifact:

- JSON: `artifacts/gateway-smoke/agno/latest.json`
- JSON Git blob: `f68fb113f4fde67409fafd3881f174054ac4530b`
- Markdown: `artifacts/gateway-smoke/agno/latest.md`
- Markdown Git blob: `30d09e813150e92f4f19883219ae2f7ae8967420`
- Generated: `2026-09-04T22:25:15.489941+00:00`

The source smoke artifact remains unchanged with `review_status: pending_manual_trace_review`. This review record is the separate acceptance decision, preserving the exact runtime evidence that was inspected.

## Review findings

All five canonical scenarios passed the schema-v2 smoke contract in the persisted run:

- transport compatibility: **PASS**;
- semantic quality: **PASS**;
- system safety: **PASS**;
- overall assessment: **PASS** with no failures;
- external expected truth matched in 5/5 runs;
- deterministic validation passed in 5/5 runs;
- `analysis_source` was `llm` in 5/5 runs;
- every run completed in one analysis attempt;
- every run recorded exactly one model call;
- input, output, and total token usage were non-zero in every run;
- no deterministic fallback was required;
- no gateway endpoint or provider/gateway credential was persisted in the reviewed artifacts.

The reviewed topology is:

```text
canonical scenario
        |
        v
Agno Workflow
        |
        v
Agno Agent
        |
        v
OpenAILike
        |
        | model = security-analysis
        v
LiteLLM Proxy
        |
        v
configured upstream model
```

The configured upstream value `openai/gpt-5.6-luna` remains configuration evidence derived from the committed LiteLLM config. It is not independent provider-response attestation.

## Acceptance scope

This review accepts the exact persisted smoke as evidence that the migrated Agno Workflow can execute the canonical framework-neutral workload through the governed LiteLLM alias with observable model usage and with the governed system preserving expected truth.

It does **not** convert the smoke into an official benchmark baseline. `official_baseline` remains false.

It also does not establish:

- a performance regression or improvement;
- a latency distribution;
- a framework ranking;
- statistical semantic-quality stability;
- general prompt-injection resistance;
- gateway retry/fallback behavior;
- multi-provider routing behavior;
- virtual-key, budget, rate-limit, or spend policy behavior;
- independent provider model attestation.

The per-scenario latencies in the artifact are descriptive only. One execution per scenario is insufficient for a performance conclusion.

## Decision

The exact persisted smoke identified above is **accepted after manual review** as post-migration compatibility evidence for the Agno-to-LiteLLM path.

This acceptance is sufficient to unblock the stale direct-model metadata cleanup tracked by Issue #73.
