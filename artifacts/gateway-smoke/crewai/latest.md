# CrewAI LiteLLM Gateway Smoke

Generated: `2026-09-04T14:47:42.718603+00:00`

Artifact type: `gateway_smoke`

Official baseline: **no**

Review status: `pending_manual_trace_review`

Client model alias: `security-analysis`

Configured upstream model: `openai/gpt-5.6-luna`

The upstream value above comes from the committed LiteLLM configuration; it is configuration evidence, not independent provider-response attestation.

Gateway endpoint and credentials are intentionally not persisted in this artifact.

Smoke assessment: **PASS**

| Runtime | Scenario | Expected match | Validation | Attempts | Calls | Tokens | Latency ms | Source |
|---|---|---:|---:|---:|---:|---:|---:|---|
| agent_crew | baseline-mixed | yes | pass | 1 | 1 | 1197 | 4454.96 | llm |
| agent_crew | product-mismatch | yes | pass | 1 | 1 | 1069 | 3045.98 | llm |
| agent_crew | unknown-version | yes | pass | 1 | 1 | 1081 | 2948.57 | llm |
| agent_crew | fixed-boundary | yes | pass | 1 | 1 | 1232 | 4242.78 | llm |
| agent_crew | adversarial-asset-id | yes | pass | 1 | 1 | 1103 | 3243.63 | llm |
| flow | baseline-mixed | yes | pass | 1 | 1 | 678 | 3391.76 | llm |
| flow | product-mismatch | yes | pass | 1 | 1 | 596 | 2329.02 | llm |
| flow | unknown-version | yes | pass | 1 | 1 | 577 | 3228.17 | llm |
| flow | fixed-boundary | yes | pass | 1 | 1 | 690 | 2588.99 | llm |
| flow | adversarial-asset-id | yes | pass | 1 | 1 | 630 | 2355.64 | llm |

## Interpretation

This smoke verifies two distinct CrewAI integration surfaces: the Agent/Task/Crew path with application-owned evaluation and the direct LLM path inside CrewAI Flow. Both must preserve expected truth and deterministic validation while exercising the governed LiteLLM alias.

Agent/Crew usage is accumulated across separate Crew kickoffs when the application evaluator retries. Flow usage comes from `flow.usage_metrics`, which aggregates LLM calls inside one Flow kickoff.

The smoke performs one execution per canonical scenario per runtime. It is compatibility evidence and must not be used as a performance baseline or framework ranking.
