# Five-Way Agentic Framework Benchmark

## Methodology

- Model: `security-analysis`
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
| First-attempt acceptance | 100.0% | 100.0% | 100.0% | 93.3% | 100.0% |
| Mean model calls | 1.00 | 1.00 | 1.00 | 1.07 | 1.00 |
| Mean latency | 3404.92 ms | 2987.15 ms | 3172.98 ms | 3214.98 ms | 2980.14 ms |
| p50 latency | 3447.83 ms | 3049.42 ms | 3082.20 ms | 2727.60 ms | 3015.20 ms |
| p95 latency* | 4651.89 ms | 3694.42 ms | 5436.80 ms | 5938.46 ms | 3597.15 ms |
| Mean total tokens | 611.33 | 1136.60 | 630.60 | 732.20 | 632.00 |
| Total tokens | 9170 | 17049 | 9459 | 10983 | 9480 |

\* At n=15, nearest-rank p95 is the sample maximum and is not a stable tail estimate.

## Agno Workflow comparisons

- vs LangGraph tokens: **+3.38%**
- vs CrewAI Flow tokens: **+0.22%**
- vs LlamaIndex Workflow tokens: **-13.68%**
- vs CrewAI Agent/Crew tokens: **-44.40%**

Agno Workflow eliminated **96.06%** of the Agent/Crew token excess above LangGraph.
The three lighter orchestration variants have a token spread of only **16.11%**.
Agno differs from CrewAI Flow by **1.40 tokens/run** and from LlamaIndex Workflow by **-100.20 tokens/run**.

## Agno Workflow latency deltas

- vs LangGraph: mean **-12.48%**, p50 **-12.55%**
- vs CrewAI Flow: mean **-6.08%**, p50 **-2.17%**
- vs LlamaIndex Workflow: mean **-7.30%**, p50 **+10.54%**
- vs CrewAI Agent/Crew: mean **-0.23%**, p50 **-1.12%**

## Scenario mean tokens

| Scenario | LangGraph | CrewAI Agent/Crew | CrewAI Flow | LlamaIndex Workflow | Agno Workflow |
| --- | ---: | ---: | ---: | ---: | ---: |
| baseline-mixed | 649.00 | 1188.33 | 680.33 | 754.00 | 676.00 |
| product-mismatch | 557.00 | 1073.00 | 580.33 | 853.00 | 597.00 |
| unknown-version | 580.00 | 1076.67 | 579.33 | 625.33 | 579.67 |
| fixed-boundary | 667.00 | 1217.33 | 677.67 | 740.33 | 693.67 |
| adversarial-asset-id | 603.67 | 1127.67 | 635.33 | 688.33 | 613.67 |

## Scenario p50 latency

| Scenario | LangGraph | CrewAI Agent/Crew | CrewAI Flow | LlamaIndex Workflow | Agno Workflow |
| --- | ---: | ---: | ---: | ---: | ---: |
| baseline-mixed | 3858.94 ms | 3358.31 ms | 3551.98 ms | 3162.50 ms | 3015.20 ms |
| product-mismatch | 2991.75 ms | 2731.65 ms | 2820.80 ms | 3754.23 ms | 2800.08 ms |
| unknown-version | 3288.34 ms | 2571.21 ms | 2468.73 ms | 2183.59 ms | 2855.24 ms |
| fixed-boundary | 3351.61 ms | 3194.63 ms | 3069.09 ms | 3108.72 ms | 3309.36 ms |
| adversarial-asset-id | 3544.80 ms | 3212.23 ms | 3135.52 ms | 2727.60 ms | 3109.00 ms |

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
