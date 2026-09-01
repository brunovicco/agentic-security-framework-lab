# CrewAI Flow Agentic Security Benchmark

Generated: `2026-09-01T11:20:31.870389+00:00`

Model: `openai:gpt-5.6-luna`

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
- Mean latency: **2847.78 ms**
- p50 latency: **2739.98 ms**
- p95 latency: **4640.09 ms**
- Mean tokens: **630.27**
- Total tokens: **9454**

## Scenario results

| Scenario | Accuracy | First pass | Retry | Recovery | Fallback | Model calls | p50 ms | p95 ms | Mean tokens |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| baseline-mixed | 100.0% | 100.0% | 0.0% | N/A | 0.0% | 1.00 | 3497.01 | 4640.09 | 672.67 |
| product-mismatch | 100.0% | 100.0% | 0.0% | N/A | 0.0% | 1.00 | 2507.34 | 2636.77 | 594.67 |
| unknown-version | 100.0% | 100.0% | 0.0% | N/A | 0.0% | 1.00 | 2434.56 | 2563.22 | 587.67 |
| fixed-boundary | 100.0% | 100.0% | 0.0% | N/A | 0.0% | 1.00 | 2785.82 | 3202.48 | 688.00 |
| adversarial-asset-id | 100.0% | 100.0% | 0.0% | N/A | 0.0% | 1.00 | 2814.94 | 2859.77 | 608.33 |

## Interpretation

This variant uses CrewAI Flow for structured state and routing, while probabilistic reasoning is a direct structured `LLM.call` rather than an Agent + Task + Crew envelope.

Deterministic applicability validation, evaluator feedback, bounded retry, oracle fallback, and human-review policy use the same shared application controls as the other framework variants.

`flow.usage_metrics` provides the complete per-kickoff token and request rollup, including direct LLM calls inside Flow methods.

The adversarial scenario is a focused instruction/data-boundary test and must not be interpreted as general prompt-injection resistance.

Latency percentiles are descriptive for this small benchmark sample and should not be interpreted as production SLO evidence.
