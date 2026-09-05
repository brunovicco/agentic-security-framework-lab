# Agno Workflow Agentic Security Benchmark

Generated: `2026-09-05T13:18:41.679127+00:00`

Model: `security-analysis`

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
- Mean latency: **2980.14 ms**
- p50 latency: **3015.20 ms**
- p95 latency: **3597.15 ms**
- Mean tokens: **632.00**
- Total tokens: **9480**

## Scenario results

| Scenario | Accuracy | First pass | Retry | Recovery | Fallback | Model calls | p50 ms | p95 ms | Mean tokens |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| baseline-mixed | 100.0% | 100.0% | 0.0% | N/A | 0.0% | 1.00 | 3015.20 | 3357.78 | 676.00 |
| product-mismatch | 100.0% | 100.0% | 0.0% | N/A | 0.0% | 1.00 | 2800.08 | 3022.39 | 597.00 |
| unknown-version | 100.0% | 100.0% | 0.0% | N/A | 0.0% | 1.00 | 2855.24 | 2949.70 | 579.67 |
| fixed-boundary | 100.0% | 100.0% | 0.0% | N/A | 0.0% | 1.00 | 3309.36 | 3597.15 | 693.67 |
| adversarial-asset-id | 100.0% | 100.0% | 0.0% | N/A | 0.0% | 1.00 | 3109.00 | 3118.90 | 613.67 |

## Interpretation

This variant uses native Agno `Workflow`, `Loop`, `Step`, and `Condition` primitives for evaluator-optimizer orchestration and a structured Agno Agent for probabilistic reasoning.

Deterministic applicability validation, evaluator feedback, bounded retry, oracle fallback, and human-review policy use the same shared application controls as the other framework variants.

Framework-level step retries are disabled (`max_retries=0`), deterministic workflow failures are fail-closed, and Agno Workflow telemetry is disabled so the application-owned evaluator remains the only retry authority.

Each measured execution creates a fresh Agno structured-analysis runner and a fresh native Workflow. Token/request telemetry comes from the isolated Agno model run metrics accumulated across bounded attempts.

Sampling uses the upstream provider defaults because the Agno adapter does not override temperature or other sampling parameters. Results must not be described as deterministic sampling.

The model label in post-migration runs is the governed gateway alias, not independent attestation of the upstream provider model.

The adversarial scenario is a focused instruction/data-boundary test and must not be interpreted as general prompt-injection resistance.

Latency percentiles are descriptive for this small benchmark sample and should not be interpreted as production SLO evidence.
