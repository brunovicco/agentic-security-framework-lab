# Agentic Security Framework Lab

[English](README.md) | [Português (Brasil)](README.pt-br.md)

[![quality](https://github.com/brunovicco/agentic-security-framework-lab/actions/workflows/quality.yml/badge.svg)](https://github.com/brunovicco/agentic-security-framework-lab/actions/workflows/quality.yml)

A framework-neutral engineering lab for building, securing, evaluating, and comparing **agentic AI workflows** under the same deterministic controls.

It implements the same vulnerability-analysis workload with **LangGraph, CrewAI, LlamaIndex, and Agno**, routes provider access through **LiteLLM**, validates model reasoning outside the LLM, exposes **MCP** compatibility, and emits content-free logical **OpenTelemetry** observations.

> **The central idea:** agent frameworks may own orchestration, but they should not automatically own security authority, policy, evidence, or final decisions.

## Why this project matters

Agentic frameworks make prototypes easy. Production-grade AI systems have a harder set of questions:

- What happens when the model is wrong but the workflow still needs a safe result?
- Which controls should remain deterministic and framework-independent?
- How do retries, fallback, tool boundaries, telemetry, and provider access stay governable?
- How do different orchestration abstractions compare when the workload, expected truth, model-facing alias, and validation policy are held constant?
- How do we preserve evidence about *how* a result was produced instead of reporting only final accuracy?

This repository turns those questions into executable architecture, tests, benchmark evidence, and explicit trade-offs.

## Read this repo based on your role

| Audience | Start here | What you can evaluate quickly |
| --- | --- | --- |
| **Developer / AI Engineer** | [Development guide](docs/DEVELOPMENT.md) → [Architecture](docs/ARCHITECTURE.md) | boundaries, typed contracts, adapters, retries, fallback, MCP, OTel, reproducibility |
| **Engineering Manager / CIO / Architect** | [Executive overview](docs/EXECUTIVE_OVERVIEW.md) → [Framework decision matrix](docs/FRAMEWORK_DECISION_MATRIX.md) | governance model, provider boundary, operational trade-offs, framework portability, evidence discipline |
| **Recruiter / Interviewer** | this README → [Executive overview](docs/EXECUTIVE_OVERVIEW.md) | project scope, engineering ownership, technologies, measurable evaluation, security and platform thinking |
| **Security / Governance reviewer** | [Architecture](docs/ARCHITECTURE.md) → [Security evidence](docs/security/) | trust boundaries, deterministic controls, adversarial experiments, telemetry/privacy constraints |

See the complete [documentation map](docs/README.md).

## What the project demonstrates

### Architecture and AI engineering

- framework-neutral Domain and Application layers;
- framework adapters below stable application contracts;
- structured LLM output with deterministic post-validation;
- evaluator-optimizer control loops with bounded retry;
- deterministic oracle fallback when probabilistic reasoning is rejected;
- explicit separation between application analysis attempts and actual model calls;
- provider-neutral model access through a governed LiteLLM alias;
- framework-specific retry suppression where hidden retries would distort evidence;
- immutable provider-backed evaluation artifacts tied to an exact Git commit.

### Security and governance

- the LLM reasons over evidence but does not own the security-sensitive source of truth;
- evidence identity and applicability are validated outside the model;
- untrusted evidence has no instruction authority by default;
- deterministic policy controls human-review requirements;
- framework proprietary telemetry is suppressed where relevant to preserve the project privacy boundary;
- logical OpenTelemetry contains safe execution metadata, not prompts, responses, rationale, evidence, credentials, or provider payloads;
- provider/model mapping stays behind the gateway instead of leaking into every framework adapter.

### Platform and interoperability

- LangGraph evaluator-optimizer;
- CrewAI Agent / Task / Crew;
- CrewAI Flow with direct structured LLM calls;
- LlamaIndex Workflow with typed events;
- Agno Workflow with native loop/condition primitives;
- LiteLLM as the centralized provider-access boundary;
- MCP v2 compatibility plus a real local STDIO host/client smoke;
- provider-free CI for quality, typing, security, MCP compatibility, and OTel contract checks.

## Core invariant

```text
LLM reasons
software validates
policy constrains
runtime executes
evidence explains
```

The LLM is a probabilistic reasoning component, not the final authority.

```text
                    ┌────────────────────────────┐
                    │  deterministic evidence    │
                    └─────────────┬──────────────┘
                                  │
                                  ▼
                     probabilistic analysis
                                  │
                                  ▼
                    deterministic evaluator
                       │                    │
                    accepted             rejected
                       │                    │
                       │              bounded retry
                       │                    │
                       │              evaluator again
                       │                    │
                       │              exhausted?
                       │                    │
                       │                    ▼
                       │          deterministic oracle
                       └──────────────┬─────┘
                                      ▼
                           deterministic policy
                                      │
                                      ▼
                               AnalysisResult
```

A correct final system result therefore does **not** necessarily mean the LLM was correct on the first attempt. That distinction between **model quality** and **system safety** is one of the main lessons of the lab.

## v1.0 evaluation snapshot

The accepted Phase 15 evaluation runs five orchestration variants against the same scenario set through the same governed LiteLLM alias.

```text
Governed client alias: security-analysis
Scenarios: 5
Repetitions per scenario: 3
Runs per variant: 15
Framework executions: 75
Actual model calls: 76
Evaluated commit: dd48c2490fc4ec1c76093577f7944d76a6fbc572
```

| Variant | Final expected accuracy | First-pass acceptance | Mean model calls | Mean latency | Mean tokens |
| --- | ---: | ---: | ---: | ---: | ---: |
| LangGraph evaluator-optimizer | 100% | 100% | 1.00 | 3404.92 ms | **611.33** |
| CrewAI Agent + Task + Crew | 100% | 100% | 1.00 | 2987.15 ms | 1136.60 |
| CrewAI Flow + direct structured LLM | 100% | 100% | 1.00 | 3172.98 ms | 630.60 |
| LlamaIndex Workflow + `structured_predict()` | 100% | **93.33%** | **1.07** | 3214.98 ms | 732.20 |
| Agno Workflow + native `Loop` / `Condition` | 100% | 100% | 1.00 | **2980.14 ms** | 632.00 |

### The most important result is not a framework winner

All five variants reached the expected final result under the same application-owned controls. The useful engineering observation is that **orchestration abstraction changed execution characteristics even when security authority and the provider boundary stayed shared**.

The CrewAI comparison makes this especially visible: Agent/Crew and Flow solved the same workload inside the same framework but produced materially different token envelopes in this sample.

The single LlamaIndex `product-mismatch` execution is also intentionally preserved:

```text
LLM attempt 1 → rejected
LLM attempt 2 → rejected
deterministic oracle fallback → expected final result
```

That execution explains why 75 framework executions produced **76 actual model calls**. The lab preserves this anomaly because evidence about recovery behavior is more valuable than cosmetically uniform benchmark output.

### What these numbers do not prove

- They do not establish statistical significance or production SLOs.
- Fifteen runs per variant are not enough for universal latency rankings.
- The results do not prove that one framework is generally superior.
- The adversarial scenarios are controlled tests, not proof of broad prompt-injection resistance.
- The `security-analysis` alias is a governed client identity, not independent attestation of the provider-native model selected behind the gateway.

Canonical evidence:

- [Phase 15 five-way report](artifacts/final-evaluation/phase15-20260905-v2/benchmarks/comparison/five-way-latest.md)
- [Machine-readable comparison](artifacts/final-evaluation/phase15-20260905-v2/benchmarks/comparison/five-way-latest.json)
- [Evaluation manifest](artifacts/final-evaluation/phase15-20260905-v2/manifest.json)
- [Final-evaluation methodology](docs/evaluation/FINAL_EVALUATION.md)

Historical provider-direct artifacts remain immutable and are intentionally not rewritten to match later gateway or runtime hardening.

## Framework implementations

| Framework / abstraction | Native orchestration | Structured reasoning path | Provider boundary | Deterministic authority |
| --- | --- | --- | --- | --- |
| LangGraph | graph nodes + conditional routing | LangChain structured output | LiteLLM `security-analysis` | Application |
| CrewAI Agent/Crew | `Agent` + `Task` + `Crew` | structured CrewAI output | LiteLLM `security-analysis` | Application evaluator |
| CrewAI Flow | Flow routing/state | direct structured `LLM.call()` | LiteLLM `security-analysis` | Application |
| LlamaIndex Workflow | typed Workflow events | `structured_predict()` | LiteLLM `security-analysis` | Application |
| Agno Workflow | `Workflow` + `Loop` + `Condition` | Agent structured output | LiteLLM `security-analysis` | Application |

Frameworks are deliberately adapters, not owners of business/security rules. See the [framework decision matrix](docs/FRAMEWORK_DECISION_MATRIX.md) for the trade-offs observed in this workload.

## Trust and provider boundaries

```text
Framework adapter
      │
      │ stable alias: security-analysis
      ▼
LiteLLM gateway
      │
      │ deployment-owned provider mapping
      ▼
LLM provider
```

The framework clients know the stable alias and gateway contract. Provider-native identifiers and provider credentials stay outside the framework-specific business path.

Separately, application-owned logical telemetry describes safe execution facts without automatically exporting model content:

```text
Application execution
      │
      ▼
AnalysisExecutionObservation
      │ safe allowlisted attributes only
      ▼
deployment-owned OpenTelemetry composition
```

Read [Architecture](docs/ARCHITECTURE.md), [LiteLLM gateway foundation](docs/litellm/GATEWAY_FOUNDATION.md), and [Privacy](docs/PRIVACY.md) for the detailed boundaries.

## Quickstart for developers

Requirements:

- Python 3.13
- [uv](https://docs.astral.sh/uv/)

```bash
git clone https://github.com/brunovicco/agentic-security-framework-lab.git
cd agentic-security-framework-lab
uv sync --frozen --all-groups
uv run python scripts/quality_gate.py
```

The normal quality gate is provider-free. You do **not** need an LLM API key to validate the engineering contracts, tests, typing, architecture checks, security checks, or deterministic behavior.

For focused development:

```bash
uv run python scripts/quality_gate.py --list
```

For provider-backed experiments through LiteLLM, follow the [gateway foundation guide](docs/litellm/GATEWAY_FOUNDATION.md) and [final-evaluation methodology](docs/evaluation/FINAL_EVALUATION.md). Provider-backed final evaluation is intentionally separate from normal CI.

Read the full [development guide](docs/DEVELOPMENT.md) before changing framework adapters, evaluation evidence, gateway policy, or telemetry contracts.

## Repository map

```text
src/agentic_lab/
├── domain/          # framework-neutral business concepts and invariants
├── application/     # use cases, evaluator/policy semantics, ports
└── adapters/        # LangGraph, CrewAI, LlamaIndex, Agno, gateway integrations

config/litellm/      # governed provider-access configuration
scripts/             # benchmarks, evaluation, quality gates, compatibility smokes
docs/                # architecture, ADRs, security, evaluation, MCP, privacy
artifacts/           # immutable benchmark/evaluation evidence
tests/               # provider-free regression and contract coverage
```

## Documentation map

### Understand the project quickly

- [Documentation by audience](docs/README.md)
- [Executive / portfolio overview](docs/EXECUTIVE_OVERVIEW.md)
- [Architecture and trust boundaries](docs/ARCHITECTURE.md)
- [Framework decision matrix](docs/FRAMEWORK_DECISION_MATRIX.md)

### Build and change the code

- [Development guide](docs/DEVELOPMENT.md)
- [Engineering contract](AGENTS.md)
- [Agentic fast track](docs/AGENTIC_FAST_TRACK.md)

### Evaluate and reproduce evidence

- [Final-evaluation methodology](docs/evaluation/FINAL_EVALUATION.md)
- [Current five-way evidence](artifacts/final-evaluation/phase15-20260905-v2/benchmarks/comparison/five-way-latest.md)
- [Evaluation manifest](artifacts/final-evaluation/phase15-20260905-v2/manifest.json)

### Security, privacy, and interoperability

- [Privacy boundary](docs/PRIVACY.md)
- [Security experiments](docs/security/)
- [MCP overview](docs/MCP.md)
- [LiteLLM gateway foundation](docs/litellm/GATEWAY_FOUNDATION.md)
- [Architecture decision records](docs/adr/)

## What makes this a portfolio project rather than a framework demo

The repository is intentionally built around engineering decisions that survive framework replacement:

1. **Domain and policy stay framework-neutral.**
2. **Probabilistic output is validated by deterministic software.**
3. **Failure behavior is observable instead of hidden.**
4. **Provider access is centralized behind a stable boundary.**
5. **Telemetry has an explicit privacy contract.**
6. **Benchmark evidence is persisted and tied to source state.**
7. **Trade-offs are documented instead of reduced to “framework X wins.”**

Those are the parts intended to be reusable when reasoning about enterprise agent platforms, AI gateways, governed runtimes, LLMOps, AI security, or framework selection.

## Project status

The planned v1.0 engineering scope is complete: domain baseline, deterministic controls, RAG progression, four framework families / five orchestration variants, benchmark comparison, LiteLLM, MCP, observability, final evaluation, runtime hardening, and portfolio documentation.

The repository remains an engineering lab, not a claim of production certification. Future work can extend the experiments without rewriting the accepted historical evidence.

See [CHANGELOG.md](CHANGELOG.md) for release-level changes.
