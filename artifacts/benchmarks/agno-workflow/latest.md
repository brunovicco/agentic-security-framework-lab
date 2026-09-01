# Agno Workflow Agentic Security Benchmark

Generated: `2026-09-01T16:07:02.540041+00:00`

Model: `openai:gpt-5.6-luna`

Framework: `agno`

Pattern: `workflow_loop_condition_evaluator_optimizer`

## Overall results

- Scenarios: **5**
- Total runs: **15**
- Expected accuracy: **100.0%**
- First-attempt acceptance: **100.0%**
- Retry rate: **0.0%**
- Recovery rate: **N/A**
- Fallback rate: **0.0%**
- Mean model calls: **1.00**
- Mean latency: **3268.84 ms**
- p50 latency: **3159.27 ms**
- p95 latency: **4966.26 ms**
- Mean tokens: **634.20**
- Total tokens: **9513**

## Scenario results

| Scenario | Accuracy | First pass | Retry | Recovery | Fallback | Model calls | p50 ms | p95 ms | Mean tokens |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| baseline-mixed | 100.0% | 100.0% | 0.0% | N/A | 0.0% | 1.00 | 4065.84 | 4966.26 | 688.33 |
| product-mismatch | 100.0% | 100.0% | 0.0% | N/A | 0.0% | 1.00 | 2779.31 | 2917.98 | 570.00 |
| unknown-version | 100.0% | 100.0% | 0.0% | N/A | 0.0% | 1.00 | 2755.51 | 3433.87 | 585.67 |
| fixed-boundary | 100.0% | 100.0% | 0.0% | N/A | 0.0% | 1.00 | 3395.40 | 4219.73 | 714.33 |
| adversarial-asset-id | 100.0% | 100.0% | 0.0% | N/A | 0.0% | 1.00 | 2970.00 | 3172.60 | 612.67 |

## Interpretation

This variant uses native Agno `Workflow`, `Loop`, `Step`, and `Condition` primitives for evaluator-optimizer orchestration and a structured Agno Agent for probabilistic reasoning.

Deterministic applicability validation, evaluator feedback, bounded retry, oracle fallback, and human-review policy use the same shared application controls as the other framework variants.

Framework-level step retries are disabled (`max_retries=0`), deterministic workflow failures are fail-closed, and Agno Workflow telemetry is disabled so the application-owned evaluator remains the only retry authority.

Each measured execution creates a fresh Agno structured-analysis runner and a fresh native Workflow. Token/request telemetry comes from the isolated Agno model run metrics accumulated across bounded attempts.

Sampling uses the OpenAI provider defaults because the Agno adapter does not override temperature or other sampling parameters. Results must not be described as deterministic sampling.

The adversarial scenario is a focused instruction/data-boundary test and must not be interpreted as general prompt-injection resistance.

Latency percentiles are descriptive for this small benchmark sample and should not be interpreted as production SLO evidence.
