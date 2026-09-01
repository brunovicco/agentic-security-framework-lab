# Four-Way Agentic Framework Benchmark

## Methodology

- Model: `openai:gpt-5.6-luna`
- Scenarios: 5
- Repetitions per scenario: 3
- Runs per variant: 15
- Shared dataset and expected truth: yes
- Shared deterministic evaluator, retry, fallback, and human-review policy: yes
- Sampling: provider default
- CrewAI Flow execution: headless
- LlamaIndex Workflow execution: native async

## Overall results

| Metric | LangGraph | CrewAI Agent/Crew | CrewAI Flow | LlamaIndex Workflow |
| --- | ---: | ---: | ---: | ---: |
| Expected accuracy | 100.0% | 100.0% | 100.0% | 100.0% |
| First-attempt acceptance | 100.0% | 100.0% | 100.0% | 100.0% |
| Mean model calls | 1.00 | 1.00 | 1.00 | 1.00 |
| Mean latency | 2728.01 ms | 2866.79 ms | 2847.78 ms | 2963.03 ms |
| p50 latency | 2643.41 ms | 2818.60 ms | 2739.98 ms | 2837.52 ms |
| p95 latency* | 3526.02 ms | 3925.60 ms | 4640.09 ms | 4394.55 ms |
| Mean total tokens | 613.80 | 1143.33 | 630.27 | 630.13 |
| Total tokens | 9207 | 17150 | 9454 | 9452 |

\* At n=15, nearest-rank p95 is the sample maximum and is not a stable tail estimate.

## Key comparisons

- CrewAI Agent/Crew vs LangGraph mean tokens: **+86.27%**
- CrewAI Flow vs LangGraph mean tokens: **+2.68%**
- LlamaIndex Workflow vs LangGraph mean tokens: **+2.66%**
- LlamaIndex Workflow vs CrewAI Flow mean tokens: **-0.02%**
- LlamaIndex Workflow vs CrewAI Agent/Crew mean tokens: **-44.89%**

CrewAI Flow eliminated **96.89%** of the Agent/Crew token excess above LangGraph.
LlamaIndex Workflow eliminated **96.92%** of the same excess.
The two lighter orchestration variants differ by only **0.14 tokens/run** (**0.02% spread**).

## LlamaIndex Workflow latency deltas

- vs LangGraph: mean **+8.62%**, p50 **+7.34%**
- vs CrewAI Flow: mean **+4.05%**, p50 **+3.56%**
- vs CrewAI Agent/Crew: mean **+3.36%**, p50 **+0.67%**

## Scenario mean tokens

| Scenario | LangGraph | CrewAI Agent/Crew | CrewAI Flow | LlamaIndex Workflow |
| --- | ---: | ---: | ---: | ---: |
| baseline-mixed | 679.67 | 1227.33 | 672.67 | 678.67 |
| product-mismatch | 565.67 | 1072.67 | 594.67 | 586.00 |
| unknown-version | 575.67 | 1082.00 | 587.67 | 574.33 |
| fixed-boundary | 658.33 | 1207.67 | 688.00 | 688.33 |
| adversarial-asset-id | 589.67 | 1127.00 | 608.33 | 623.33 |

## Scenario p50 latency

| Scenario | LangGraph | CrewAI Agent/Crew | CrewAI Flow | LlamaIndex Workflow |
| --- | ---: | ---: | ---: | ---: |
| baseline-mixed | 3210.34 ms | 3295.65 ms | 3497.01 ms | 3542.82 ms |
| product-mismatch | 2323.92 ms | 2552.76 ms | 2507.34 ms | 2704.44 ms |
| unknown-version | 2672.45 ms | 2449.23 ms | 2434.56 ms | 2601.50 ms |
| fixed-boundary | 2734.86 ms | 3075.73 ms | 2785.82 ms | 2956.46 ms |
| adversarial-asset-id | 2597.10 ms | 2787.34 ms | 2814.94 ms | 2837.52 ms |

## Interpretation

Under this controlled small benchmark, both CrewAI Flow with a direct structured LLM call and LlamaIndex Workflows with `structured_predict()` landed very close to the LangGraph token baseline.

The much larger Agent/Task/Crew token footprint therefore should not be generalized to CrewAI as a framework. For this workload, the selected orchestration abstraction had a larger effect on token consumption than the difference between the lighter framework implementations.

All four official variants reached 100% expected accuracy and 100% first-attempt acceptance in these fifteen-run samples, so this benchmark does not establish a quality ranking among the frameworks.

The adversarial asset-ID scenario remains a narrow instruction/data-boundary test and is not evidence of general prompt-injection resistance.

Latency is descriptive only. No statistical-significance or production-SLO claim should be made from these samples.

## Limitations

- The benchmark uses five synthetic scenarios and three repetitions per scenario.
- Latency values are descriptive and must not be interpreted as production SLO evidence.
- At n=15, nearest-rank p95 resolves to the sample maximum, so mean and p50 are more useful for this comparison.
- The adversarial asset-id scenario is a narrow instruction/data-boundary test and is not evidence of general prompt-injection resistance.
- All variants share application-owned deterministic validation, retry, fallback, policy, dataset, and expected truth while intentionally using different framework orchestration abstractions.
- Token usage represents end-to-end framework-specific prompt and orchestration behavior for this workload.
- The sample is too small to support statistical-significance claims or general framework rankings.
