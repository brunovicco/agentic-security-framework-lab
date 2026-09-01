# Five-Way Agentic Framework Benchmark

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
- Agno Workflow execution: native sync

## Overall results

| Metric | LangGraph | CrewAI Agent/Crew | CrewAI Flow | LlamaIndex Workflow | Agno Workflow |
| --- | ---: | ---: | ---: | ---: | ---: |
| Expected accuracy | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| First-attempt acceptance | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| Mean model calls | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| Mean latency | 2728.01 ms | 2866.79 ms | 2847.78 ms | 2963.03 ms | 3268.84 ms |
| p50 latency | 2643.41 ms | 2818.60 ms | 2739.98 ms | 2837.52 ms | 3159.27 ms |
| p95 latency* | 3526.02 ms | 3925.60 ms | 4640.09 ms | 4394.55 ms | 4966.26 ms |
| Mean total tokens | 613.80 | 1143.33 | 630.27 | 630.13 | 634.20 |
| Total tokens | 9207 | 17150 | 9454 | 9452 | 9513 |

\* At n=15, nearest-rank p95 is the sample maximum and is not a stable tail estimate.

## Agno Workflow comparisons

- vs LangGraph tokens: **+3.32%**
- vs CrewAI Flow tokens: **+0.62%**
- vs LlamaIndex Workflow tokens: **+0.65%**
- vs CrewAI Agent/Crew tokens: **-44.53%**

Agno Workflow eliminated **96.15%** of the Agent/Crew token excess above LangGraph.
The three lighter orchestration variants have a token spread of only **0.65%**.
Agno differs from CrewAI Flow by **3.93 tokens/run** and from LlamaIndex Workflow by **4.07 tokens/run**.

## Agno Workflow latency deltas

- vs LangGraph: mean **+19.83%**, p50 **+19.51%**
- vs CrewAI Flow: mean **+14.79%**, p50 **+15.30%**
- vs LlamaIndex Workflow: mean **+10.32%**, p50 **+11.34%**
- vs CrewAI Agent/Crew: mean **+14.02%**, p50 **+12.09%**

## Scenario mean tokens

| Scenario | LangGraph | CrewAI Agent/Crew | CrewAI Flow | LlamaIndex Workflow | Agno Workflow |
| --- | ---: | ---: | ---: | ---: | ---: |
| baseline-mixed | 679.67 | 1227.33 | 672.67 | 678.67 | 688.33 |
| product-mismatch | 565.67 | 1072.67 | 594.67 | 586.00 | 570.00 |
| unknown-version | 575.67 | 1082.00 | 587.67 | 574.33 | 585.67 |
| fixed-boundary | 658.33 | 1207.67 | 688.00 | 688.33 | 714.33 |
| adversarial-asset-id | 589.67 | 1127.00 | 608.33 | 623.33 | 612.67 |

## Scenario p50 latency

| Scenario | LangGraph | CrewAI Agent/Crew | CrewAI Flow | LlamaIndex Workflow | Agno Workflow |
| --- | ---: | ---: | ---: | ---: | ---: |
| baseline-mixed | 3210.34 ms | 3295.65 ms | 3497.01 ms | 3542.82 ms | 4065.84 ms |
| product-mismatch | 2323.92 ms | 2552.76 ms | 2507.34 ms | 2704.44 ms | 2779.31 ms |
| unknown-version | 2672.45 ms | 2449.23 ms | 2434.56 ms | 2601.50 ms | 2755.51 ms |
| fixed-boundary | 2734.86 ms | 3075.73 ms | 2785.82 ms | 2956.46 ms | 3395.40 ms |
| adversarial-asset-id | 2597.10 ms | 2787.34 ms | 2814.94 ms | 2837.52 ms | 2970.00 ms |

## Interpretation

Under this controlled small benchmark, CrewAI Flow, LlamaIndex Workflow, and Agno Workflow all landed close to the LangGraph token baseline.

The substantially larger Agent/Task/Crew token footprint therefore should not be generalized to CrewAI as a framework. For this workload, orchestration abstraction choice had a much larger effect on token consumption than the difference among the lighter implementations.

Agno Workflow used slightly more tokens than CrewAI Flow and LlamaIndex Workflow, while showing higher mean and p50 latency in this fifteen-run sample. These latency results are descriptive only and do not establish a general framework ranking.

All five official variants reached 100% expected accuracy and 100% first-attempt acceptance, so this benchmark does not establish a quality ranking among frameworks.

The adversarial asset-ID scenario remains a narrow instruction/data-boundary test and is not evidence of general prompt-injection resistance.

## Limitations

- The benchmark uses five synthetic scenarios and three repetitions per scenario.
- Latency values are descriptive and must not be interpreted as production SLO evidence.
- At n=15, nearest-rank p95 resolves to the sample maximum, so mean and p50 are more useful for this comparison.
- The adversarial asset-id scenario is a narrow instruction/data-boundary test and is not evidence of general prompt-injection resistance.
- All variants share application-owned deterministic validation, retry, fallback, policy, dataset, and expected truth while intentionally using different framework orchestration abstractions.
- Token usage represents end-to-end framework-specific prompt and orchestration behavior for this workload.
- The sample is too small to support statistical-significance claims or general framework rankings.
