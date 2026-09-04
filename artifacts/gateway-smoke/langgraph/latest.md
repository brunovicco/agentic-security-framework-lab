# LangGraph LiteLLM Gateway Smoke

Generated: `2026-09-04T13:20:07.699003+00:00`

Artifact type: `gateway_smoke`

Official baseline: **no**

Review status: `pending_manual_trace_review`

Client model alias: `security-analysis`

Configured upstream model: `openai/gpt-5.6-luna`

The upstream value above comes from the committed LiteLLM configuration; it is configuration evidence, not independent provider-response attestation.

Gateway endpoint and credentials are intentionally not persisted in this artifact.

Smoke assessment: **PASS**

| Scenario | Expected match | Validation | Attempts | Calls | Tokens | Latency ms | Source |
|---|---:|---:|---:|---:|---:|---:|---|
| baseline-mixed | yes | pass | 1 | 1 | 682 | 3215.37 | llm |
| product-mismatch | yes | pass | 1 | 1 | 561 | 2341.17 | llm |
| unknown-version | yes | pass | 1 | 1 | 585 | 2241.94 | llm |
| fixed-boundary | yes | pass | 1 | 1 | 653 | 2135.61 | llm |
| adversarial-asset-id | yes | pass | 1 | 1 | 581 | 9601.77 | llm |

## Interpretation

This smoke verifies that the migrated LangGraph client can execute the canonical framework-neutral workload through the governed LiteLLM alias while preserving deterministic validation and expected truth.

It is intentionally one execution per scenario and must not be used as a performance baseline or framework ranking.
