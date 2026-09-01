# CrewAI Flow Real Retry Recovery Observation

## Observation

A real evaluator retry occurred during the pre-headless CrewAI Flow benchmark.

- Model: `openai:gpt-5.6-luna`
- Scenario: `product-mismatch`
- Iteration: 1
- Analysis attempts: **2**
- Model calls: **2**
- Final validation passed: **yes**
- Final expected result matched: **yes**
- Oracle fallback used: **no**
- Total tokens: **1224**

## Control path

```text
first LLM draft
      |
      v
deterministic evaluator
      |
      | rejected
      v
bounded retry with evaluator feedback
      |
      v
second LLM draft
      |
      v
deterministic evaluator
      |
      | accepted
      v
correct final system result
```

This is the first real benchmark observation in this project where the
evaluator-optimizer recovery path was exercised rather than only proven
through deterministic tests.

## Latency exclusion

Latency from this observation is intentionally **not used** in the
cross-framework comparison.

At the time of this run, CrewAI Flow console events were rendered inside
the measured execution window. The subsequent official benchmark uses
`suppress_flow_events=True` and is the canonical source for Flow latency.

## Limitations

- This is one observed recovery, not a retry-rate estimate.
- The complete rejected first draft was not persisted.
- This demonstrates the bounded recovery control path, not general model reliability.
