# CrewAI Flow Agentic Security Benchmark

Generated: `2026-09-05T13:17:04.837599+00:00`

Model: `security-analysis`

Framework: `crewai`

Pattern: `flow_direct_llm_evaluator_optimizer`

## Overall results

- Scenarios: **5**
- Total runs: **15**
- Expected accuracy: **100.0%**
- First-attempt acceptance: **100.0%**
- Retry rate: **0.0%**
- Recovery rate: **N/A**
- Fallback rate: **0.0%**
- Mean model calls: **1.00**
- Mean latency: **3172.98 ms**
- p50 latency: **3082.20 ms**
- p95 latency: **5436.80 ms**
- Mean tokens: **630.60**
- Total tokens: **9459**

## Scenario results

| Scenario | Accuracy | First pass | Retry | Recovery | Fallback | Model calls | p50 ms | p95 ms | Mean tokens |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| baseline-mixed | 100.0% | 100.0% | 0.0% | N/A | 0.0% | 1.00 | 3551.98 | 5436.80 | 680.33 |
| product-mismatch | 100.0% | 100.0% | 0.0% | N/A | 0.0% | 1.00 | 2820.80 | 3254.95 | 580.33 |
| unknown-version | 100.0% | 100.0% | 0.0% | N/A | 0.0% | 1.00 | 2468.73 | 3159.65 | 579.33 |
| fixed-boundary | 100.0% | 100.0% | 0.0% | N/A | 0.0% | 1.00 | 3069.09 | 3136.69 | 677.67 |
| adversarial-asset-id | 100.0% | 100.0% | 0.0% | N/A | 0.0% | 1.00 | 3135.52 | 3504.98 | 635.33 |

## Interpretation

This variant uses CrewAI Flow for structured state and routing, while probabilistic reasoning is a direct structured `LLM.call` rather than an Agent + Task + Crew envelope.

Deterministic applicability validation, evaluator feedback, bounded retry, oracle fallback, and human-review policy use the same shared application controls as the other framework variants.

`flow.usage_metrics` provides the complete per-kickoff token and request rollup, including direct LLM calls inside Flow methods.

The adversarial scenario is a focused instruction/data-boundary test and must not be interpreted as general prompt-injection resistance.

Latency percentiles are descriptive for this small benchmark sample and should not be interpreted as production SLO evidence.
