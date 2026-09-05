# CrewAI Agentic Security Benchmark

Generated: `2026-09-05T13:16:14.743097+00:00`

Model: `security-analysis`

Framework: `crewai`

Pattern: `single_agent_external_evaluator_optimizer`

## Overall results

- Scenarios: **5**
- Total runs: **15**
- Expected accuracy: **100.0%**
- First-attempt acceptance: **100.0%**
- Retry rate: **0.0%**
- Recovery rate: **N/A**
- Fallback rate: **0.0%**
- Mean model calls: **1.00**
- Mean latency: **2987.15 ms**
- p50 latency: **3049.42 ms**
- p95 latency: **3694.42 ms**
- Mean tokens: **1136.60**
- Total tokens: **17049**

## Scenario results

| Scenario | Accuracy | First pass | Retry | Recovery | Fallback | Model calls | p50 ms | p95 ms | Mean tokens |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| baseline-mixed | 100.0% | 100.0% | 0.0% | N/A | 0.0% | 1.00 | 3358.31 | 3457.57 | 1188.33 |
| product-mismatch | 100.0% | 100.0% | 0.0% | N/A | 0.0% | 1.00 | 2731.65 | 2862.99 | 1073.00 |
| unknown-version | 100.0% | 100.0% | 0.0% | N/A | 0.0% | 1.00 | 2571.21 | 2789.82 | 1076.67 |
| fixed-boundary | 100.0% | 100.0% | 0.0% | N/A | 0.0% | 1.00 | 3194.63 | 3341.90 | 1217.33 |
| adversarial-asset-id | 100.0% | 100.0% | 0.0% | N/A | 0.0% | 1.00 | 3212.23 | 3694.42 | 1127.67 |

## Interpretation

`expected_accuracy` compares the final system result with the framework-neutral evaluation dataset.

The CrewAI baseline uses one structured Agent + Task + Crew for probabilistic reasoning. Deterministic evaluation, bounded retry, fallback, and human-review policy remain application-owned.

`analysis_attempts` counts application-level evaluator cycles. `model_calls` comes from CrewAI `successful_requests`, so it may exceed the number of analysis attempts if CrewAI performs extra provider requests internally.

The adversarial scenario tests whether instruction-like text embedded in untrusted asset data influences classification. It is a focused security test, not proof of general prompt-injection resistance.

Latency percentiles are descriptive for this benchmark sample size and should not be interpreted as production SLO measurements.
