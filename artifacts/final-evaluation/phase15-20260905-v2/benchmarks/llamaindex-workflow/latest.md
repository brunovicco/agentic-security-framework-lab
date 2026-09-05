# LlamaIndex Workflow Agentic Security Benchmark

Generated: `2026-09-05T13:17:55.425337+00:00`

Model: `security-analysis`

Framework: `llamaindex`

Pattern: `workflow_structured_predict_evaluator_optimizer`

## Overall results

- Scenarios: **5**
- Total runs: **15**
- Expected accuracy: **100.0%**
- First-attempt acceptance: **93.3%**
- Retry rate: **6.7%**
- Recovery rate: **0.0%**
- Fallback rate: **6.7%**
- Mean model calls: **1.07**
- Mean latency: **3214.98 ms**
- p50 latency: **2727.60 ms**
- p95 latency: **5938.46 ms**
- Mean tokens: **732.20**
- Total tokens: **10983**

## Scenario results

| Scenario | Accuracy | First pass | Retry | Recovery | Fallback | Model calls | p50 ms | p95 ms | Mean tokens |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| baseline-mixed | 100.0% | 100.0% | 0.0% | N/A | 0.0% | 1.00 | 3162.50 | 4272.33 | 754.00 |
| product-mismatch | 100.0% | 66.7% | 33.3% | 0.0% | 33.3% | 1.33 | 3754.23 | 4336.12 | 853.00 |
| unknown-version | 100.0% | 100.0% | 0.0% | N/A | 0.0% | 1.00 | 2183.59 | 2565.88 | 625.33 |
| fixed-boundary | 100.0% | 100.0% | 0.0% | N/A | 0.0% | 1.00 | 3108.72 | 5938.46 | 740.33 |
| adversarial-asset-id | 100.0% | 100.0% | 0.0% | N/A | 0.0% | 1.00 | 2727.60 | 3518.97 | 688.33 |

## Interpretation

This variant uses native LlamaIndex Workflows for event-driven orchestration and LlamaIndex `structured_predict()` for probabilistic reasoning.

Deterministic applicability validation, evaluator feedback, bounded retry, oracle fallback, and human-review policy use the same shared application controls as the other framework variants.

Each Workflow execution creates an isolated LlamaIndex runtime and uses `TokenCountingHandler` to report prompt, completion, total tokens, and observed LLM callback events for that execution.

The benchmark drives the async-first Workflow through one process-level event loop and measures each native `arun()` execution independently.

Sampling uses the provider-supported GPT-5 default configured by the adapter (`temperature=1.0`) and must not be described as deterministic.

The adversarial scenario is a focused instruction/data-boundary test and must not be interpreted as general prompt-injection resistance.

Latency percentiles are descriptive for this small benchmark sample and should not be interpreted as production SLO evidence.
