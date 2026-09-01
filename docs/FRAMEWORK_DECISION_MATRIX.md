# Framework Decision Matrix

This document translates the five-way benchmark into an engineering decision aid.

It is **not** a universal ranking of agentic frameworks. The evidence comes from one controlled vulnerability-analysis workload with five scenarios, three repetitions per scenario, and fifteen runs per variant.

## Benchmark context

All official variants share:

- model: `openai:gpt-5.6-luna`;
- provider-default sampling;
- the same evidence and expected truth;
- the same deterministic applicability evaluator;
- the same bounded retry semantics;
- the same deterministic oracle fallback;
- the same human-review policy;
- the same final application contract.

Only the orchestration abstraction changes.

## Overall benchmark snapshot

| Variant | Expected accuracy | First pass | Mean latency | p50 latency | Mean tokens |
| --- | ---: | ---: | ---: | ---: | ---: |
| LangGraph evaluator-optimizer | 100% | 100% | **2728.01 ms** | **2643.41 ms** | **613.80** |
| CrewAI Agent + Task + Crew | 100% | 100% | 2866.79 ms | 2818.60 ms | 1143.33 |
| CrewAI Flow + direct structured LLM | 100% | 100% | 2847.78 ms | 2739.98 ms | 630.27 |
| LlamaIndex Workflow + `structured_predict()` | 100% | 100% | 2963.03 ms | 2837.52 ms | 630.13 |
| Agno Workflow + `Loop` / `Condition` | 100% | 100% | 3268.84 ms | 3159.27 ms | 634.20 |

At `n=15`, nearest-rank p95 is the sample maximum and is intentionally omitted from the decision matrix as a primary metric.

## Decision matrix

| Dimension | LangGraph | CrewAI Agent/Task/Crew | CrewAI Flow | LlamaIndex Workflow | Agno Workflow |
| --- | --- | --- | --- | --- | --- |
| Control-flow style | explicit graph + conditional edges | role/task/crew abstraction | flow/state orchestration | typed event workflow | workflow + loop + condition |
| Structured reasoning surface | LangChain structured model output | structured CrewAI result | direct structured `LLM.call()` | `structured_predict()` | structured Agent output |
| Application-owned evaluator | yes | yes, external to Crew | yes | yes | yes |
| Bounded retry controlled by application | yes | yes | yes | yes | yes |
| Framework hidden retry risk observed | low in benchmark path | higher-level abstraction may add behavior | explicitly controlled | workflow path controlled | `Step.max_retries` required explicit override |
| Framework telemetry concern | normal model/runtime telemetry | framework envelope | headless execution required for fair latency | callback/token counting surface | Workflow telemetry explicitly disabled |
| Native persistence used in benchmark | no | no | no | no Context persistence | no |
| Mean tokens/run | **613.80** | 1143.33 | 630.27 | 630.13 | 634.20 |
| Token delta vs LangGraph | baseline | +86.27% | +2.68% | +2.66% | +3.32% |
| Mean latency vs LangGraph | baseline | +5.09% | +4.39% | +8.62% | +19.83% |
| Abstraction visibility | high | lower-level runtime details abstracted | medium/high | high through typed events | medium/high |
| Best fit demonstrated by this lab | explicit governed state machine | testing higher-level agent/task envelope | lightweight CrewAI orchestration | async typed workflow orchestration | concise native loop/condition orchestration |

## How to read these results

### LangGraph

**What this lab demonstrates well**

- Explicit graph topology makes security-relevant routing visible.
- Conditional transitions map naturally to evaluator-optimizer behavior.
- The official sample produced the lowest mean tokens and lowest mean/p50 latency.
- It is straightforward to keep deterministic validation outside the model.

**Tradeoff**

The explicit graph model can require more orchestration code than higher-level agent abstractions. That extra code can be a benefit when auditability matters, but it is still code that must be maintained.

**Use when**

You want explicit state transitions, predictable routing, and a security review that can reason about the workflow as a graph.

### CrewAI Agent + Task + Crew

**What this lab demonstrates well**

- The abstraction is expressive for role-oriented agent/task composition.
- It can still be placed behind an external deterministic evaluator and policy boundary.
- Final quality was identical to the other official samples under the shared controls.

**Tradeoff observed here**

The `Agent + Task + Crew` envelope used materially more tokens than every lighter orchestration path in this workload: **1143.33 tokens/run** versus roughly **614–634** for the others.

This should not be generalized to “CrewAI is expensive.” The CrewAI Flow result is the counterexample inside the same framework.

**Use when**

The semantics of agents, tasks, roles, delegation, or crew composition are themselves useful enough to justify the higher-level abstraction.

### CrewAI Flow

**What this lab demonstrates well**

- Keeps CrewAI's Flow routing/state abstraction without the larger Agent/Task/Crew prompt envelope.
- Token use moved to within **2.68%** of the LangGraph baseline.
- It removed **96.89%** of the Agent/Crew token excess above LangGraph.

**Important implementation detail**

The official benchmark runs headlessly. Earlier console rendering inside measured execution contaminated latency, so presentation output was removed from the measured path.

**Use when**

You want CrewAI's workflow abstraction but do not need the full Agent/Task/Crew envelope for every reasoning call.

### LlamaIndex Workflow

**What this lab demonstrates well**

- Typed events make workflow state transitions explicit.
- `structured_predict()` maps cleanly to the shared structured analysis contract.
- Token use was effectively tied with CrewAI Flow: **630.13 vs 630.27 tokens/run**.
- Native async execution fits naturally into async-first applications.

**Important implementation detail**

The benchmark intentionally does not use Context persistence/checkpoint serialization. State travels through typed events to avoid adding an unrelated persistence/serialization surface to the comparison.

**Use when**

You value typed async workflow events and already use LlamaIndex components or async orchestration patterns.

### Agno Workflow

**What this lab demonstrates well**

- Native `Workflow`, `Loop`, `Step`, and `Condition` express the bounded evaluator-optimizer compactly.
- Mean token use stayed in the same lightweight cluster: **634.20 tokens/run**.
- It removed **96.15%** of the Agent/Crew excess above LangGraph.

**Tradeoff observed here**

Agno showed higher latency in this sample: mean latency was **19.83% above LangGraph**, **14.79% above CrewAI Flow**, and **10.32% above LlamaIndex Workflow**.

This is descriptive evidence from fifteen runs, not a general performance claim.

**Security-relevant default discovered**

Agno `Step` retries required an explicit `max_retries=0` override for benchmark-sensitive steps. Otherwise framework retries could occur outside the application-governed evaluator retry path. Workflow telemetry was also explicitly disabled.

**Use when**

You want concise native workflow/loop/condition primitives and are willing to make framework defaults explicit for governed execution.

## Token-cost interpretation

The most important token result is the shape of the distribution:

```text
LangGraph                613.80
LlamaIndex Workflow      630.13
CrewAI Flow              630.27
Agno Workflow            634.20
CrewAI Agent/Crew       1143.33
```

The three lighter orchestration variants added after LangGraph span only **0.65%** in mean tokens.

That means this benchmark provides stronger evidence for:

> abstraction choice matters

than for:

> framework brand determines cost

The CrewAI comparison is especially useful because two abstractions inside the same framework produced very different token envelopes.

## Security architecture interpretation

From a security-engineering perspective, the preferred framework is not necessarily the one with the smallest metric.

The more important questions are:

1. Can the LLM be prevented from authorizing its own output?
2. Can validation remain deterministic and framework-neutral?
3. Can hidden retries be bounded or disabled?
4. Can framework telemetry be understood and controlled?
5. Can untrusted data remain distinct from instructions?
6. Can runtime evidence explain whether success came from the LLM, retry, or fallback?
7. Can the framework be replaced without rewriting security policy?

All five variants in this lab were deliberately engineered to answer those questions through shared application-owned controls.

## Practical selection guide

Use this as a starting point, not a universal prescription:

| If your priority is... | Candidate to evaluate first | Why |
| --- | --- | --- |
| explicit governed state transitions | LangGraph | graph topology and conditional routing are directly visible |
| role/task-oriented multi-agent semantics | CrewAI Agent/Task/Crew | abstraction directly models agents, tasks, and crews |
| CrewAI with a lighter reasoning envelope | CrewAI Flow | near-baseline token use in this workload |
| typed async event workflows | LlamaIndex Workflow | native event-driven async orchestration |
| compact workflow/loop/condition primitives | Agno Workflow | native control primitives express bounded loops concisely |

Then evaluate the candidate under **your own** workload, model, tools, security requirements, latency environment, and production controls.

## What would change this matrix

The decision matrix should be revisited when the lab adds:

- tool calls and MCP authorization;
- multi-agent delegation;
- memory and persistence;
- richer prompt-injection scenarios;
- human approval steps;
- provider/model variation;
- larger latency samples;
- production-grade tracing and observability.

Those features may change which framework abstraction is easiest to govern and may expose cost or security differences that this current benchmark intentionally excludes.

## Evidence

Canonical comparison artifacts:

- [`five-way-latest.md`](../artifacts/benchmarks/comparison/five-way-latest.md)
- [`five-way-latest.json`](../artifacts/benchmarks/comparison/five-way-latest.json)

Architecture and authority boundaries:

- [`ARCHITECTURE.md`](ARCHITECTURE.md)
