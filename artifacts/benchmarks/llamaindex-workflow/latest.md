# LlamaIndex Workflow Agentic Security Benchmark

Generated: `2026-09-01T14:30:17.210141+00:00`

Model: `openai:gpt-5.6-luna`

Framework: `llamaindex`

Pattern: `workflow_structured_predict_evaluator_optimizer`

## Overall results

- Scenarios: **5**
- Total runs: **15**
- Expected accuracy: **100.0%**
- First-attempt acceptance: **100.0%**
- Retry rate: **0.0%**
- Recovery rate: **N/A**
- Fallback rate: **0.0%**
- Mean model calls: **1.00**
- Mean latency: **2963.03 ms**
- p50 latency: **2837.52 ms**
- p95 latency: **4394.55 ms**
- Mean tokens: **630.13**
- Total tokens: **9452**

## Scenario results

| Scenario | Accuracy | First pass | Retry | Recovery | Fallback | Model calls | p50 ms | p95 ms | Mean tokens |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| baseline-mixed | 100.0% | 100.0% | 0.0% | N/A | 0.0% | 1.00 | 3542.82 | 4394.55 | 678.67 |
| product-mismatch | 100.0% | 100.0% | 0.0% | N/A | 0.0% | 1.00 | 2704.44 | 2772.19 | 586.00 |
| unknown-version | 100.0% | 100.0% | 0.0% | N/A | 0.0% | 1.00 | 2601.50 | 2835.80 | 574.33 |
| fixed-boundary | 100.0% | 100.0% | 0.0% | N/A | 0.0% | 1.00 | 2956.46 | 3256.84 | 688.33 |
| adversarial-asset-id | 100.0% | 100.0% | 0.0% | N/A | 0.0% | 1.00 | 2837.52 | 3135.63 | 623.33 |

## Interpretation

This variant uses native LlamaIndex Workflows for event-driven orchestration and LlamaIndex `structured_predict()` for probabilistic reasoning.

Deterministic applicability validation, evaluator feedback, bounded retry, oracle fallback, and human-review policy use the same shared application controls as the other framework variants.

Each Workflow execution creates an isolated LlamaIndex runtime and uses `TokenCountingHandler` to report prompt, completion, total tokens, and observed LLM callback events for that execution.

The benchmark drives the async-first Workflow through one process-level event loop and measures each native `arun()` execution independently.

Sampling uses the provider-supported GPT-5 default configured by the adapter (`temperature=1.0`) and must not be described as deterministic.

The adversarial scenario is a focused instruction/data-boundary test and must not be interpreted as general prompt-injection resistance.

Latency percentiles are descriptive for this small benchmark sample and should not be interpreted as production SLO evidence.
