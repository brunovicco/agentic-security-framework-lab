# Executive overview

## What this project is

Agentic Security Framework Lab is a controlled engineering environment for comparing agentic AI orchestration approaches under the same security-sensitive workload and the same application-owned controls.

The project implements one vulnerability-analysis problem across:

- LangGraph;
- CrewAI Agent / Task / Crew;
- CrewAI Flow;
- LlamaIndex Workflow;
- Agno Workflow.

All current provider-backed paths use a centralized LiteLLM gateway alias, while deterministic application code remains responsible for validating evidence, applicability, fallback, and final policy.

## Why this matters to an engineering organization

The main architectural question is not "which agent framework is best?"

It is:

> Which responsibilities should remain stable and governable even when frameworks, providers, or orchestration abstractions change?

The lab demonstrates one answer:

```text
frameworks orchestrate
models reason
deterministic software validates
policy constrains
provider access is centralized
evidence is persisted
```

That separation is relevant to organizations building shared AI platforms, governed agent runtimes, LLM gateways, or multiple domain-specific agents that should inherit common controls.

## Management-level capabilities demonstrated

### 1. Framework portability

Business and security rules stay outside framework adapters. This reduces the architectural cost of experimenting with or replacing orchestration libraries.

### 2. Governed provider access

Framework clients use the stable `security-analysis` alias while provider/model mapping remains behind LiteLLM. This demonstrates a provider-neutral control point rather than hard-coding provider identities across application code.

### 3. Deterministic authority around probabilistic reasoning

The LLM can propose structured analysis, but deterministic software validates the security-sensitive facts before a final result is accepted.

### 4. Bounded failure recovery

The system distinguishes:

- a correct first-pass model result;
- a result recovered after retry;
- a deterministic fallback after model output remains invalid.

This matters because final accuracy alone can hide operationally important failure behavior.

### 5. Evidence-driven framework comparison

The repository uses a shared dataset, common expected truth, common model-facing alias, common repetition count, and persisted immutable artifacts. The goal is to compare execution characteristics without moving the target between frameworks.

### 6. Privacy-aware observability

Logical OpenTelemetry is separated from provider/framework tracing. The application observation contract is intentionally content-free and does not include prompts, responses, rationale, evidence, credentials, or provider payloads by default.

### 7. Interoperability boundaries

The project includes MCP v2 compatibility and a real local STDIO host/client smoke, while keeping MCP transport concerns outside the Domain layer.

## v1.0 evaluation evidence

The accepted five-way evaluation contains:

```text
5 orchestration variants
5 scenarios
3 repetitions per scenario
75 framework executions
76 actual model calls
100% expected final accuracy for every variant
```

One LlamaIndex execution required an additional model attempt before deterministic fallback. The artifact is preserved rather than normalized because the project treats recovery behavior as evidence.

The benchmark also showed different token envelopes across orchestration approaches in this sample, including a substantial difference between CrewAI Agent/Crew and CrewAI Flow even though both belong to the same framework family.

See:

- [five-way evaluation report](../artifacts/final-evaluation/phase15-20260905-v2/benchmarks/comparison/five-way-latest.md);
- [machine-readable comparison](../artifacts/final-evaluation/phase15-20260905-v2/benchmarks/comparison/five-way-latest.json);
- [evaluation manifest](../artifacts/final-evaluation/phase15-20260905-v2/manifest.json);
- [framework decision matrix](FRAMEWORK_DECISION_MATRIX.md).

## What the benchmark should not be used to claim

The evidence is intentionally bounded.

It does **not** establish:

- statistically significant framework rankings;
- production SLOs;
- universal prompt-injection resistance;
- independent attestation of the provider-native model behind the gateway alias;
- production certification.

The project is strongest as an architecture and engineering evidence base, not as a marketing benchmark.

## What this demonstrates in a portfolio or interview

The repository provides concrete examples of reasoning about:

- AI platform architecture;
- agent framework selection;
- deterministic guardrails;
- secure-by-design trust boundaries;
- LLM gateway patterns;
- retries and fallback ownership;
- MCP integration boundaries;
- OpenTelemetry and privacy;
- evaluation methodology;
- immutable evidence and reproducibility;
- typed Python architecture and CI quality gates.

A concise way to explain the architecture is:

> "The frameworks orchestrate probabilistic reasoning, but the application keeps security authority. Every framework crosses the same governed model boundary, produces the same domain-facing contract, and is evaluated against external expected truth. That lets us compare orchestration without moving policy or trust into the framework."

## Suggested reading by decision

| If you want to understand... | Read... |
| --- | --- |
| architecture and trust boundaries | [ARCHITECTURE.md](ARCHITECTURE.md) |
| which framework abstraction fit which trade-off | [FRAMEWORK_DECISION_MATRIX.md](FRAMEWORK_DECISION_MATRIX.md) |
| provider/model governance | [litellm/GATEWAY_FOUNDATION.md](litellm/GATEWAY_FOUNDATION.md) |
| current benchmark methodology | [evaluation/FINAL_EVALUATION.md](evaluation/FINAL_EVALUATION.md) |
| privacy and telemetry | [PRIVACY.md](PRIVACY.md) |
| security/adversarial experiments | [security/](security/) |
| developer workflow | [DEVELOPMENT.md](DEVELOPMENT.md) |
