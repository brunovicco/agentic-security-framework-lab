# LangGraph vs CrewAI Benchmark

## Methodology

- Model: `openai:gpt-5.6-luna`
- Scenarios: 5
- Repetitions per scenario: 3
- Runs per framework: 15
- Shared dataset and expected truth: yes
- Shared deterministic validation and fallback policy: yes
- Sampling: provider default

## Overall results

| Metric | LangGraph | CrewAI | CrewAI vs LangGraph |
| --- | ---: | ---: | ---: |
| Expected accuracy | 100.0% | 100.0% | +0.00 pp |
| First-attempt acceptance | 100.0% | 100.0% | +0.00 pp |
| Retry rate | 0.0% | 0.0% | +0.00 pp |
| Fallback rate | 0.0% | 0.0% | +0.00 pp |
| Mean model calls | 1.00 | 1.00 | — |
| Mean latency | 2728.01 ms | 2866.79 ms | +5.09% |
| p50 latency | 2643.41 ms | 2818.60 ms | +6.63% |
| p95 latency | 3526.02 ms | 3925.60 ms | +11.33% |
| Mean total tokens | 613.80 | 1143.33 | +86.27% |
| Total tokens | 9207 | 17150 | +7943 |

## Scenario comparison

| Scenario | LG p50 | CrewAI p50 | Latency Δ | LG tokens | CrewAI tokens | Token Δ |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline-mixed | 3210.34 ms | 3295.65 ms | +2.66% | 679.67 | 1227.33 | +80.58% |
| product-mismatch | 2323.92 ms | 2552.76 ms | +9.85% | 565.67 | 1072.67 | +89.63% |
| unknown-version | 2672.45 ms | 2449.23 ms | -8.35% | 575.67 | 1082.00 | +87.95% |
| fixed-boundary | 2734.86 ms | 3075.73 ms | +12.46% | 658.33 | 1207.67 | +83.44% |
| adversarial-asset-id | 2597.10 ms | 2787.34 ms | +7.33% | 589.67 | 1127.00 | +91.12% |

## Interpretation

Both frameworks reached 100% expected accuracy and 100% first-attempt acceptance across the persisted 15-run benchmark.

For this workload, CrewAI used **1.863x** the mean tokens of LangGraph (+86.27%) while mean latency was +5.09% higher.

The result therefore shows quality parity in this dataset but a material difference in orchestration/token overhead.

## Security interpretation

Both frameworks passed the narrow adversarial asset-id scenario in all three persisted runs without triggering retry or fallback.

This demonstrates correct behavior for this specific instruction-data-boundary test only. It is not evidence of general prompt-injection resistance.

## Limitations

- The benchmark contains five synthetic scenarios with three repetitions each; latency percentiles are descriptive, not production SLO evidence.
- The adversarial asset-id scenario tests a narrow indirect prompt-injection boundary and must not be interpreted as general prompt-injection resistance.
- No live retry or fallback was triggered in either persisted 15-run benchmark; those paths are covered separately by deterministic tests.
- Token differences include framework-specific prompt and orchestration overhead and therefore represent end-to-end framework behavior for this workload.
