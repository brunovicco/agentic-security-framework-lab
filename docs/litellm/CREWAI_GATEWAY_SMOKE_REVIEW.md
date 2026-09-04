# CrewAI LiteLLM Gateway Smoke Review

Review decision: **accepted_manual_trace_review**

Reviewed at: `2026-09-04T14:53:19+00:00`

Reviewed against repository commit: `bb7ec5bfeee1f08d08b413639315c9bffde7ae60`

Source artifact:

- JSON: `artifacts/gateway-smoke/crewai/latest.json`
- JSON Git blob: `26c13ad2895e43e7322d7f5ab11ea27b7116dcd2`
- Markdown: `artifacts/gateway-smoke/crewai/latest.md`
- Markdown Git blob: `6ec45ffde41b621b9e499b92b1656c5fab8fbc46`
- Generated: `2026-09-04T14:47:42.718603+00:00`

The source smoke artifact remains unchanged with `review_status: pending_manual_trace_review`. This review record is the separate acceptance decision, preserving the exact runtime evidence that was inspected.

## Review findings

All ten executions passed the smoke contract across both migrated CrewAI runtime surfaces:

- external expected truth matched in 10/10 runs;
- deterministic validation passed in 10/10 runs;
- `analysis_source` was `llm` in 10/10 runs;
- every run completed in one analysis attempt;
- every run recorded exactly one model call;
- token usage was non-zero in every run;
- no deterministic fallback was required;
- the final smoke assessment was `PASS` with no failures;
- no gateway endpoint or provider/gateway credential was persisted in the reviewed artifacts.

Runtime coverage was:

- 5/5 canonical scenarios through CrewAI Agent/Task/Crew with the application-owned evaluator-optimizer;
- 5/5 canonical scenarios through CrewAI Flow with direct structured `LLM.call(...)` inside the Flow runtime.

The reviewed topology is:

```text
canonical scenarios
        |
        +-----------------------------+
        |                             |
        v                             v
CrewAI Agent/Task/Crew          CrewAI Flow
        |                             |
        +--------------+--------------+
                       |
                       | model = security-analysis
                       v
                  LiteLLM Proxy
                       |
                       v
              configured upstream model
```

The configured upstream value `openai/gpt-5.6-luna` remains configuration evidence derived from the committed LiteLLM config. It is not independent provider-response attestation.

## Telemetry correction before acceptance

The first provider-backed CrewAI smoke execution was intentionally not persisted as accepted evidence. It passed functional behavior but exposed that CrewAI 1.15.18 reports Agent/Crew token usage as a cumulative process snapshot across successive kickoffs. The initial smoke interpretation therefore produced `model_calls` values `1, 2, 3, 4, 5` across scenarios.

PR #51 corrected the runtime to retain the cumulative snapshot and let `consume_usage()` calculate per-scenario deltas. The reviewed artifact above was generated only after that correction. In the accepted run, every Agent/Crew scenario reports one analysis attempt and one model call, matching the observed execution boundary.

This distinction matters because correct final behavior is not sufficient evidence when telemetry semantics are wrong. The diagnostic run was useful for debugging, but it was not promoted into the evidence set.

## Acceptance scope

This review accepts the smoke as evidence that both migrated CrewAI integration surfaces can execute the framework-neutral canonical workload through the governed LiteLLM alias while preserving expected truth and deterministic validation.

It does **not** convert the smoke into an official benchmark baseline. `official_baseline` remains false.

It also does not establish:

- a performance regression or improvement;
- a latency distribution;
- a framework ranking between Agent/Crew, Flow, LangGraph, or other frameworks;
- general prompt-injection resistance;
- gateway retry/fallback behavior;
- multi-provider routing behavior;
- virtual-key, budget, rate-limit, or spend policy behavior;
- independent provider model attestation.

The observed latencies and token totals are retained as descriptive runtime evidence only. With one execution per scenario per runtime, they are insufficient for performance conclusions.

## Decision

The exact persisted smoke identified above is **accepted after manual review** as post-migration compatibility evidence for both CrewAI-to-LiteLLM paths.
