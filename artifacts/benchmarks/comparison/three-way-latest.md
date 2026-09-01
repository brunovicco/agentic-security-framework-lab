# LangGraph vs CrewAI Agent/Crew vs CrewAI Flow

## Methodology

- Model: `openai:gpt-5.6-luna`
- Scenarios: 5
- Repetitions per scenario: 3
- Runs per variant: 15
- Shared dataset and expected truth: yes
- Shared deterministic evaluator and fallback policy: yes
- Sampling: provider default
- CrewAI Flow execution: headless

## Overall results

| Metric | LangGraph | CrewAI Agent/Crew | CrewAI Flow |
| --- | ---: | ---: | ---: |
| Expected accuracy | 100.0% | 100.0% | 100.0% |
| First-attempt acceptance | 100.0% | 100.0% | 100.0% |
| Retry rate | 0.0% | 0.0% | 0.0% |
| Fallback rate | 0.0% | 0.0% | 0.0% |
| Mean model calls | 1.00 | 1.00 | 1.00 |
| Mean latency | 2728.01 ms | 2866.79 ms | 2847.78 ms |
| p50 latency | 2643.41 ms | 2818.60 ms | 2739.98 ms |
| p95* latency | 3526.02 ms | 3925.60 ms | 4640.09 ms |
| Mean total tokens | 613.80 | 1143.33 | 630.27 |
| Total tokens | 9207 | 17150 | 9454 |

\* With 15 observations, nearest-rank p95 is the sample maximum and should be interpreted cautiously.

## Efficiency deltas

### CrewAI Agent/Crew vs LangGraph

- Mean tokens: **+86.27%**
- Mean latency: **+5.09%**
- p50 latency: **+6.63%**

### CrewAI Flow vs LangGraph

- Mean tokens: **+2.68%**
- Mean latency: **+4.39%**
- p50 latency: **+3.65%**

### CrewAI Flow vs CrewAI Agent/Crew

- Mean tokens: **-44.87%**
- Mean latency: **-0.66%**
- p50 latency: **-2.79%**

## Token overhead decomposition

CrewAI Agent/Crew introduced **529.53** additional mean tokens per run relative to LangGraph.

CrewAI Flow reduced the remaining difference to **16.47** tokens per run.

Therefore the Flow variant eliminated **96.89%** of the Agent/Crew token overhead observed above the LangGraph baseline.

## Scenario token comparison

| Scenario | LangGraph | Agent/Crew | Flow | Flow vs LG | Flow vs Agent |
| --- | ---: | ---: | ---: | ---: | ---: |
| baseline-mixed | 679.67 | 1227.33 | 672.67 | -1.03% | -45.19% |
| product-mismatch | 565.67 | 1072.67 | 594.67 | +5.13% | -44.56% |
| unknown-version | 575.67 | 1082.00 | 587.67 | +2.08% | -45.69% |
| fixed-boundary | 658.33 | 1207.67 | 688.00 | +4.51% | -43.03% |
| adversarial-asset-id | 589.67 | 1127.00 | 608.33 | +3.16% | -46.02% |

## Scenario p50 latency comparison

| Scenario | LangGraph | Agent/Crew | Flow | Flow vs LG | Flow vs Agent |
| --- | ---: | ---: | ---: | ---: | ---: |
| baseline-mixed | 3210.34 ms | 3295.65 ms | 3497.01 ms | +8.93% | +6.11% |
| product-mismatch | 2323.92 ms | 2552.76 ms | 2507.34 ms | +7.89% | -1.78% |
| unknown-version | 2672.45 ms | 2449.23 ms | 2434.56 ms | -8.90% | -0.60% |
| fixed-boundary | 2734.86 ms | 3075.73 ms | 2785.82 ms | +1.86% | -9.43% |
| adversarial-asset-id | 2597.10 ms | 2787.34 ms | 2814.94 ms | +8.39% | +0.99% |

## Interpretation

All three persisted variants achieved 100% final expected accuracy and 100% first-attempt acceptance in their official 15-run benchmark artifacts.

For this workload, the main difference was not measured output quality but orchestration overhead.

CrewAI Agent/Task/Crew used materially more tokens than LangGraph, while CrewAI Flow with a direct structured LLM call returned close to the LangGraph token baseline.

This suggests that abstraction choice inside the same framework can materially affect token cost.

## Security interpretation

All three official variants passed the narrow adversarial asset-id scenario in all three runs.

The deterministic evaluator, bounded retry, oracle fallback, and human-review policy remain application-owned controls rather than model-owned decisions.

This is evidence only for the specific tested instruction/data boundary and is not proof of general prompt-injection resistance.

## Limitations

- The benchmark uses five synthetic scenarios and three repetitions per scenario.
- Latency values are descriptive and must not be interpreted as production SLO evidence.
- At n=15, nearest-rank p95 resolves to the sample maximum, so mean and p50 are more useful for this comparison.
- The adversarial asset-id scenario is a narrow instruction/data-boundary test and is not evidence of general prompt-injection resistance.
- The three variants intentionally use different framework orchestration abstractions while sharing the same application-owned deterministic evaluator, fallback, policy, dataset, and expected truth.
- Token usage includes framework-specific prompt and orchestration overhead and represents end-to-end behavior for this workload.
