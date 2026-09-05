# Framework Decision Matrix

This document translates the current gateway-backed five-way evaluation into an engineering decision aid.

It is **not** a universal ranking of agentic frameworks. The evidence comes from one controlled vulnerability-analysis workload with five scenarios, three repetitions per scenario, and fifteen framework executions per variant.

The earlier provider-direct five-way artifacts remain valid historical evidence. This matrix uses the immutable Phase 15 final-evaluation bundle as the current-state source instead of rewriting those historical artifacts.

## Current evaluation context

All five variants share:

- governed client-facing model alias: `security-analysis`;
- centralized LiteLLM gateway boundary;
- provider-default sampling;
- the same five framework-neutral scenarios;
- the same evidence and expected truth;
- the same deterministic applicability evaluator;
- the same bounded retry semantics;
- the same deterministic oracle fallback;
- the same human-review policy;
- the same final application contract.

Only the orchestration abstraction and its framework-specific runtime path change.

The alias identifies the governed model name requested by each framework. It is intentionally not treated as independent attestation of the provider-native model selected behind the gateway.

## Final-evaluation snapshot

| Variant | Expected accuracy | First pass | Mean calls | Mean latency | p50 latency | Mean tokens |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| LangGraph evaluator-optimizer | 100% | 100% | 1.00 | 3404.92 ms | 3447.83 ms | **611.33** |
| CrewAI Agent + Task + Crew | 100% | 100% | 1.00 | 2987.15 ms | 3049.42 ms | 1136.60 |
| CrewAI Flow + direct structured LLM | 100% | 100% | 1.00 | 3172.98 ms | 3082.20 ms | 630.60 |
| LlamaIndex Workflow + `structured_predict()` | 100% | **93.33%** | **1.07** | 3214.98 ms | **2727.60 ms** | 732.20 |
| Agno Workflow + `Loop` / `Condition` | 100% | 100% | 1.00 | **2980.14 ms** | 3015.20 ms | 632.00 |

Across the five variants, the final run contains 75 framework executions and 76 model calls. The extra call came from one LlamaIndex `product-mismatch` execution that used both allowed LLM attempts before deterministic oracle fallback.

At `n=15`, nearest-rank p95 resolves to the sample maximum. Mean and p50 are therefore the primary descriptive latency metrics here; none of these latency observations establish a production SLO or universal performance ranking.

## Decision matrix

| Dimension | LangGraph | CrewAI Agent/Task/Crew | CrewAI Flow | LlamaIndex Workflow | Agno Workflow |
| --- | --- | --- | --- | --- | --- |
| Control-flow style | explicit graph + conditional edges | role/task/crew abstraction | flow/state orchestration | typed event workflow | workflow + loop + condition |
| Structured reasoning surface | LangChain structured model output | structured CrewAI result | direct structured `LLM.call()` | `structured_predict()` | structured Agent output |
| Provider boundary | LiteLLM `security-analysis` | LiteLLM `security-analysis` | LiteLLM `security-analysis` | LiteLLM `security-analysis` | LiteLLM `security-analysis` |
| Application-owned evaluator | yes | yes, external to Crew | yes | yes | yes |
| Bounded retry controlled by application | yes | yes | yes | yes | yes |
| Framework hidden retry control | explicit graph path | higher-level abstraction requires explicit runtime controls | explicitly controlled | application loop remains authoritative | `Step.max_retries=0` required on benchmark-sensitive steps |
| Framework telemetry boundary | logical project telemetry stays separate | proprietary tracing explicitly disabled | proprietary tracing explicitly disabled | callback/token-counting surface remains framework-specific | vendor telemetry explicitly disabled |
| Native persistence used in benchmark | no | no | no | no Context persistence | no |
| Mean tokens/run | **611.33** | 1136.60 | 630.60 | 732.20 | 632.00 |
| Token delta vs LangGraph | baseline | +85.92% | +3.15% | +19.77% | +3.38% |
| Mean latency vs LangGraph | baseline | -12.27% | -6.81% | -5.58% | -12.48% |
| Abstraction visibility | high | lower-level runtime details abstracted | medium/high | high through typed events | medium/high |
| Best fit demonstrated by this lab | explicit governed state machine | higher-level role/task/crew semantics | lightweight CrewAI orchestration | typed async workflow orchestration | concise native loop/condition orchestration |

## How to read the results

### LangGraph

**What this lab demonstrates well**

- Explicit graph topology makes security-relevant routing visible.
- Conditional transitions map naturally to evaluator-optimizer behavior.
- The current final evaluation produced the lowest mean token count: **611.33 tokens/run**.
- Deterministic validation remains clearly outside the model and framework.

**Tradeoff observed in the final sample**

LangGraph did not have the lowest measured latency in this final run. Its 3404.92 ms mean is descriptive evidence from fifteen executions, not evidence that the graph abstraction is inherently slower.

**Use when**

You want explicit state transitions, predictable routing, and a security review that can reason about the workflow as a graph.

### CrewAI Agent + Task + Crew

**What this lab demonstrates well**

- The abstraction is expressive for role-oriented agent/task composition.
- It can remain behind an external deterministic evaluator and policy boundary.
- Final expected accuracy was identical to the other variants under the shared controls.
- The final sample had a low mean latency of 2987.15 ms.

**Tradeoff observed here**

The `Agent + Task + Crew` envelope used **1136.60 tokens/run**, materially more than LangGraph, CrewAI Flow, and Agno for this workload.

This should not be generalized to “CrewAI is expensive.” CrewAI Flow is the counterexample inside the same framework and consumed only 630.60 tokens/run.

**Use when**

The semantics of agents, tasks, roles, delegation, or crew composition are themselves useful enough to justify the higher-level abstraction.

### CrewAI Flow

**What this lab demonstrates well**

- Keeps CrewAI's Flow routing/state abstraction without the larger Agent/Task/Crew prompt envelope.
- Mean token use was only **3.15%** above the LangGraph baseline.
- It removed **96.33%** of the Agent/Crew token excess above LangGraph in this sample.
- The accepted final run stayed fully headless and did not emit the proprietary tracing prompt/link path encountered during the aborted first Phase 15 attempt.

**Use when**

You want CrewAI's workflow abstraction but do not need the full Agent/Task/Crew envelope for every reasoning call.

### LlamaIndex Workflow

**What this lab demonstrates well**

- Typed events make workflow state transitions explicit.
- `structured_predict()` maps to the shared structured analysis contract.
- Native async workflow execution fits naturally into async-first applications.
- The application-owned control path was exercised visibly rather than hidden: one execution failed deterministic validation on both allowed LLM attempts and then used the deterministic oracle fallback while preserving the expected result.

**Observed anomaly, not a framework verdict**

The final sample recorded:

- first-attempt acceptance: **93.33%**;
- total model calls: **16** for 15 framework executions;
- fallback rate: **6.67%**;
- mean tokens: **732.20**.

The extra call contributes to the higher token average, so this single run should not be interpreted as proof that LlamaIndex has a structurally larger steady-state prompt envelope. The anomaly is preserved because the benchmark is intended to expose control-path behavior, not make every framework look uniform.

The benchmark intentionally does not use Context persistence/checkpoint serialization. State travels through typed events to avoid adding an unrelated persistence surface to the comparison.

**Use when**

You value typed async workflow events and already use LlamaIndex components or async orchestration patterns.

### Agno Workflow

**What this lab demonstrates well**

- Native `Workflow`, `Loop`, `Step`, and `Condition` express the bounded evaluator-optimizer compactly.
- Mean token use stayed near the LangGraph baseline at **632.00 tokens/run** (+3.38%).
- It removed **96.06%** of the Agent/Crew token excess above LangGraph in this sample.
- The final sample had the lowest mean latency, 2980.14 ms, by only 0.23% versus CrewAI Agent/Crew.

That latency difference is far too small and the sample far too limited to support a universal winner claim.

**Security-relevant defaults**

Agno `Step` retries require an explicit `max_retries=0` override for benchmark-sensitive steps so framework retries cannot occur outside the application-governed evaluator loop. Vendor telemetry is also explicitly disabled for the benchmark runtime.

**Use when**

You want concise native workflow/loop/condition primitives and are willing to make framework defaults explicit for governed execution.

## Token-cost interpretation

The final sample has this mean-token shape:

```text
LangGraph                611.33
CrewAI Flow              630.60
Agno Workflow            632.00
LlamaIndex Workflow      732.20
CrewAI Agent/Crew       1136.60
```

CrewAI Flow and Agno were almost identical in this run: Agno used only **0.22%** more mean tokens than CrewAI Flow. Both remained close to the LangGraph baseline.

LlamaIndex sits above that cluster in the final sample, but one of its fifteen executions made an additional model call before fallback. The observed mean therefore mixes orchestration envelope and control-path activation. It should not be used to infer a stable framework tax without a larger sample that separates first-pass and retry cases.

The CrewAI comparison remains especially useful because two abstractions inside the **same framework** produced very different token envelopes. That is stronger evidence for:

> orchestration abstraction matters

than for:

> framework brand alone determines cost

## Latency interpretation

The final mean latencies are close enough that this sample should be treated descriptively:

```text
Agno Workflow            2980.14 ms
CrewAI Agent/Crew        2987.15 ms
CrewAI Flow              3172.98 ms
LlamaIndex Workflow      3214.98 ms
LangGraph                3404.92 ms
```

LlamaIndex had the lowest p50 at 2727.60 ms but also the largest observed sample tail, with a nearest-rank p95/sample maximum of 5938.46 ms. Different metrics therefore tell different stories even inside the same fifteen-run sample.

The practical conclusion is not to select a framework from these latency numbers. Re-run the candidates under the intended provider, workload, concurrency, network path, and production SLO measurement design.

## Security architecture interpretation

From a security-engineering perspective, the preferred framework is not necessarily the one with the smallest metric.

The more important questions are:

1. Can the LLM be prevented from authorizing its own output?
2. Can validation remain deterministic and framework-neutral?
3. Can hidden retries be bounded or disabled?
4. Can framework telemetry be understood and controlled?
5. Can untrusted data remain distinct from instructions?
6. Can runtime evidence explain whether success came from the LLM, retry, or fallback?
7. Can provider identity and credentials remain behind a stable gateway contract?
8. Can the framework be replaced without rewriting security policy?

All five variants in this lab were deliberately engineered to answer those questions through shared application-owned controls and the same governed gateway alias.

## Practical selection guide

Use this as a starting point, not a universal prescription:

| If your priority is... | Candidate to evaluate first | Why |
| --- | --- | --- |
| explicit governed state transitions | LangGraph | graph topology and conditional routing are directly visible |
| role/task-oriented multi-agent semantics | CrewAI Agent/Task/Crew | abstraction directly models agents, tasks, and crews |
| CrewAI with a lighter reasoning envelope | CrewAI Flow | near-baseline token use in this workload |
| typed async event workflows | LlamaIndex Workflow | native event-driven async orchestration and visible fallback path |
| compact workflow/loop/condition primitives | Agno Workflow | native control primitives express bounded loops concisely |

Then evaluate the candidate under **your own** workload, gateway/provider mapping, tools, security requirements, latency environment, and production controls.

## What would change this matrix

The decision matrix should be revisited when the lab adds or materially expands:

- tool calls and MCP authorization beyond compatibility smoke;
- multi-agent delegation;
- memory and persistence;
- richer prompt-injection scenarios;
- human approval steps;
- provider/model variation behind the gateway;
- larger latency samples and uncertainty estimates;
- deployment-grade tracing/exporter composition.

Those features may change which framework abstraction is easiest to govern and may expose cost or security differences that this current benchmark intentionally excludes.

## Evidence

Current immutable Phase 15 evidence:

- [five-way human-readable comparison](../artifacts/final-evaluation/phase15-20260905-v2/benchmarks/comparison/five-way-latest.md)
- [five-way machine-readable comparison](../artifacts/final-evaluation/phase15-20260905-v2/benchmarks/comparison/five-way-latest.json)
- [final-evaluation manifest](../artifacts/final-evaluation/phase15-20260905-v2/manifest.json)
- [final-evaluation methodology](evaluation/FINAL_EVALUATION.md)

Historical provider-direct comparison artifacts remain available without modification:

- [`five-way-latest.md`](../artifacts/benchmarks/comparison/five-way-latest.md)
- [`five-way-latest.json`](../artifacts/benchmarks/comparison/five-way-latest.json)

Architecture and authority boundaries:

- [`ARCHITECTURE.md`](ARCHITECTURE.md)
- [LiteLLM gateway foundation](litellm/GATEWAY_FOUNDATION.md)
