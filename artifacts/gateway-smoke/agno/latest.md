# Agno LiteLLM Gateway Smoke

Generated: `2026-09-04T22:25:15.489941+00:00`

Artifact type: `gateway_smoke`

Official baseline: **no**

Review status: `pending_manual_trace_review`

Client model alias: `security-analysis`

Configured upstream model: `openai/gpt-5.6-luna`

The upstream value above comes from the committed LiteLLM configuration; it is configuration evidence, not independent provider-response attestation.

Gateway endpoint and credentials are intentionally not persisted in this artifact.

Overall assessment: **PASS**
Transport compatibility: **PASS**
Semantic quality: **PASS**
System safety: **PASS**

| Scenario | Expected match | Validation | Attempts | Calls | Tokens | Latency ms | Source |
|---|---:|---:|---:|---:|---:|---:|---|
| baseline-mixed | yes | pass | 1 | 1 | 724 | 6058.48 | llm |
| product-mismatch | yes | pass | 1 | 1 | 606 | 2480.90 | llm |
| unknown-version | yes | pass | 1 | 1 | 589 | 2243.34 | llm |
| fixed-boundary | yes | pass | 1 | 1 | 720 | 2144.28 | llm |
| adversarial-asset-id | yes | pass | 1 | 1 | 626 | 2215.44 | llm |

## Interpretation

Transport compatibility checks that the Agno Workflow exercised observable model calls through the gateway boundary with complete token telemetry.

Semantic quality records whether the LLM draft passed deterministic validation without oracle fallback. System safety independently records whether final framework-neutral expected truth was preserved.

The top-level process remains fail-closed: all three dimensions must pass. The split exists so a safe fallback cannot be misreported as LLM success and a semantic model failure cannot be misreported as a broken gateway transport.

The smoke performs one execution per canonical scenario. It is compatibility evidence and must not be used as a performance baseline or framework ranking.
