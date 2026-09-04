# LlamaIndex LiteLLM Gateway Smoke

Generated: `2026-09-04T21:45:52.450738+00:00`

Artifact type: `gateway_smoke`

Official baseline: **no**

Review status: `pending_manual_trace_review`

Client model alias: `security-analysis`

Configured upstream model: `openai/gpt-5.6-luna`

The upstream value above comes from the committed LiteLLM configuration; it is configuration evidence, not independent provider-response attestation.

Gateway endpoint and credentials are intentionally not persisted in this artifact.

Overall assessment: **PASS**

## Evidence dimensions

- Transport compatibility: **PASS**
- Semantic quality: **PASS**
- System safety: **PASS**

A failed overall assessment can still contain valid transport-compatibility evidence. It must not be described as semantic LLM success when semantic quality fails.

| Scenario | Expected match | Validation | Attempts | Calls | Tokens | Latency ms | Source |
|---|---:|---:|---:|---:|---:|---:|---|
| baseline-mixed | yes | pass | 1 | 1 | 733 | 5155.69 | llm |
| product-mismatch | yes | pass | 1 | 1 | 615 | 2480.77 | llm |
| unknown-version | yes | pass | 1 | 1 | 638 | 3092.71 | llm |
| fixed-boundary | yes | pass | 1 | 1 | 751 | 4345.00 | llm |
| adversarial-asset-id | yes | pass | 1 | 1 | 694 | 3018.71 | llm |

## Interpretation

Transport compatibility proves that the LlamaIndex Workflow reached the gateway-backed provider path with complete observable usage.

Semantic quality separately records whether probabilistic LLM output passed the deterministic evaluator without requiring oracle fallback.

System safety records whether the final governed result matches external framework-neutral truth, including when deterministic fallback is required.

The overall process remains fail closed: all three evidence dimensions must pass for the smoke command to exit successfully.

The smoke performs one execution per canonical scenario. It is not a performance baseline, framework ranking, or statistical quality benchmark.
