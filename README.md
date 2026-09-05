# Agentic Security Framework Lab

[English](README.md) | [Português (Brasil)](README.pt-br.md)

[![quality](https://github.com/brunovicco/agentic-security-framework-lab/actions/workflows/quality.yml/badge.svg)](https://github.com/brunovicco/agentic-security-framework-lab/actions/workflows/quality.yml)

A framework-neutral engineering lab for building, securing, evaluating, and comparing **agentic AI workflows** under the same deterministic controls.

It implements the same vulnerability-analysis workload with **LangGraph, CrewAI, LlamaIndex, and Agno**, routes provider access through **LiteLLM**, validates model reasoning outside the LLM, exposes **MCP** compatibility, emits content-free logical **OpenTelemetry** observations, and now exercises **governed mutable agent actions** through the same application-owned authorization and enforcement boundary.

> **The central idea:** agent frameworks may own orchestration, but they should not automatically own security authority, policy, evidence, authorization, or final decisions.

## Why this project matters

Agentic frameworks make prototypes easy. Production-grade AI systems have a harder set of questions:

- What happens when the model is wrong but the workflow still needs a safe result?
- Which controls should remain deterministic and framework-independent?
- How do retries, fallback, tool boundaries, telemetry, and provider access stay governable?
- How do different orchestration abstractions compare when the workload, expected truth, model-facing alias, and validation policy are held constant?
- How do we preserve evidence about *how* a result was produced instead of reporting only final accuracy?
- What happens when an agent can propose a mutable tool action but should not be allowed to authorize itself?
- How do caller identity, least privilege, human approval, and execution evidence remain stable when frameworks or tool surfaces change?

This repository turns those questions into executable architecture, tests, benchmark evidence, and explicit trade-offs.

## Read this repo based on your role

| Audience | Start here | What you can evaluate quickly |
| --- | --- | --- |
| **Developer / AI Engineer** | [Development guide](docs/DEVELOPMENT.md) → [Architecture](docs/ARCHITECTURE.md) | boundaries, typed contracts, adapters, retries, fallback, governed actions, MCP, OTel, reproducibility |
| **Engineering Manager / CIO / Architect** | [Executive overview](docs/EXECUTIVE_OVERVIEW.md) → [Governed Agent Actions](docs/security/GOVERNED_AGENT_ACTIONS.md) | governance model, authorization, provider boundary, operational trade-offs, framework portability, evidence discipline |
| **Recruiter / Interviewer** | this README → [Executive overview](docs/EXECUTIVE_OVERVIEW.md) | project scope, engineering ownership, technologies, measurable evaluation, AI security and platform thinking |
| **Security / Governance reviewer** | [Architecture](docs/ARCHITECTURE.md) → [Governed Agent Actions](docs/security/GOVERNED_AGENT_ACTIONS.md) | trust boundaries, least privilege, HITL, runtime enforcement, adversarial tests, MCP, telemetry/privacy constraints |

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
- framework-specific retry suppression where hidden retries would distort evidence or multiply mutable side effects;
- immutable provider-backed evaluation artifacts tied to an exact Git commit;
- mutable-action orchestration that stays portable across LangGraph, CrewAI, LlamaIndex, and Agno without moving authorization into those frameworks.

### Security and governance

- the LLM reasons over evidence but does not own the security-sensitive source of truth;
- evidence identity and applicability are validated outside the model;
- untrusted evidence has no instruction authority by default;
- deterministic policy controls human-review requirements;
- model-adjacent `ProposedAction` is separated from trusted `ActionContext`;
- exact least-privilege authorization evaluates `(caller_id, identity_source, action, resource, environment)` with no cross-source fallback;
- unknown action scopes fail closed;
- `require_human_approval` remains blocked until separately sourced approval evidence is validated for the exact caller/action scope;
- authorization, approval, and actual execution are recorded as independent evidence facts;
- framework proprietary telemetry is suppressed where relevant to preserve the project privacy boundary;
- logical OpenTelemetry contains safe execution metadata, not prompts, responses, rationale, evidence, credentials, or provider payloads;
- provider/model mapping stays behind the gateway instead of leaking into every framework adapter.

### Platform and interoperability

- LangGraph evaluator-optimizer plus governed-action `StateGraph`;
- CrewAI Agent / Task / Crew;
- CrewAI Flow with direct structured LLM calls plus governed-action Flow;
- LlamaIndex Workflow with typed events plus governed-action Workflow;
- Agno Workflow with native loop/condition primitives plus a no-retry governed mutable Step;
- LiteLLM as the centralized provider-access boundary;
- MCP v2 compatibility plus real local STDIO host/client smokes for read-only applicability and governed mutable actions;
- cross-framework governed-action conformance against the direct application runtime;
- provider-free CI for quality, typing, security, MCP compatibility, governed mutable-action behavior, and OTel contract checks.

## Core invariant

```text
LLM reasons
software validates
policy constrains
runtime executes
evidence explains
```

The LLM is a probabilistic reasoning component, not the final authority.

For mutable actions, the same principle becomes:

```text
agent/model proposes
trusted context identifies the caller
policy authorizes
human evidence approves when required
runtime enforces
adapter executes
evidence proves what happened
```

And one distinction remains explicit throughout the project:

```text
tool availability != tool authorization != tool execution
```

See [Governed Agent Actions](docs/security/GOVERNED_AGENT_ACTIONS.md) for the complete v1.1 trust model.

## v1.1 engineering snapshot — Governed Agent Actions

The post-v1.0 work extends the original principle from **analysis decisions** into **mutable agent actions** without changing who owns security authority.

The current controlled boundary includes:

- frozen `ProposedAction(action, resource, environment)` as untrusted proposal data;
- separate trusted `ActionContext(caller_id, identity_source)` supplied by composition/runtime or authentication code;
- deterministic exact-scope authorization with `allow`, `deny`, and `require_human_approval` outcomes;
- trusted `HumanApprovalEvidence` bound to the exact proposal and caller context;
- `GovernedActionRuntime` as the single enforcement point before mutable execution;
- `ActionExecutionEvidence` separating authorization, approval state, and actual execution;
- a safe in-memory mutable finding acknowledgement adapter;
- framework adapters for LangGraph, CrewAI Flow, LlamaIndex Workflow, and Agno Workflow;
- adversarial tests for caller spoofing, fake approvals, tool substitution, scope escalation, and retry-after-deny;
- cross-framework conformance comparing complete evidence and observable side effects with direct application execution;
- a separate governed mutable MCP STDIO server whose tool schema cannot provide trusted caller or approval identity.

The cross-framework conformance matrix covers exact allow, explicit deny, missing approval, validated trusted approval, caller mismatch, identity-source mismatch, and resource escalation. For every framework, the expected security semantics and side-effect count must match the direct application baseline.

This is **provider-free application/framework/MCP integration evidence**. It does not claim authenticated remote identity, production-grade authorization infrastructure, provider-backed action execution, or production certification.

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

### Analysis workload

| Framework / abstraction | Native orchestration | Structured reasoning path | Provider boundary | Deterministic authority |
| --- | --- | --- | --- | --- |
| LangGraph | graph nodes + conditional routing | LangChain structured output | LiteLLM `security-analysis` | Application |
| CrewAI Agent/Crew | `Agent` + `Task` + `Crew` | structured CrewAI output | LiteLLM `security-analysis` | Application evaluator |
| CrewAI Flow | Flow routing/state | direct structured `LLM.call()` | LiteLLM `security-analysis` | Application |
| LlamaIndex Workflow | typed Workflow events | `structured_predict()` | LiteLLM `security-analysis` | Application |
| Agno Workflow | `Workflow` + `Loop` + `Condition` | Agent structured output | LiteLLM `security-analysis` | Application |

### Governed mutable action

| Framework | Framework role | Trusted context | Authorization/enforcement owner |
| --- | --- | --- | --- |
| LangGraph | one action graph node | injected outside graph input | `GovernedActionRuntime` |
| CrewAI Flow | one deterministic Flow start | constructor dependency, outside Flow state | `GovernedActionRuntime` |
| LlamaIndex Workflow | one typed event step | constructor dependency, outside StartEvent | `GovernedActionRuntime` |
| Agno Workflow | one custom Python Step | injected dependency, outside workflow input | `GovernedActionRuntime` |

Frameworks are deliberately adapters, not owners of business/security rules. See the [framework decision matrix](docs/FRAMEWORK_DECISION_MATRIX.md) for the trade-offs observed in the analysis workload and [Governed Agent Actions](docs/security/GOVERNED_AGENT_ACTIONS.md) for the mutable-action boundary.

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

Separately, governed mutable actions use a different authority path:

```text
untrusted action proposal
      +
trusted caller context
      │
      ▼
application authorization
      │
      ├─ deny ──────────────────────► evidence / no execution
      │
      ├─ require approval ─► trusted approval validation
      │                         │
      │                         └─ missing/invalid ─► no execution
      ▼
GovernedActionRuntime
      │
      ▼
mutable adapter
```

Application-owned logical telemetry describes safe analysis execution facts without automatically exporting model content:

```text
Application execution
      │
      ▼
AnalysisExecutionObservation
      │ safe allowlisted attributes only
      ▼
deployment-owned OpenTelemetry composition
```

Read [Architecture](docs/ARCHITECTURE.md), [Governed Agent Actions](docs/security/GOVERNED_AGENT_ACTIONS.md), [LiteLLM gateway foundation](docs/litellm/GATEWAY_FOUNDATION.md), and [Privacy](docs/PRIVACY.md) for the detailed boundaries.

## MCP boundary

The project keeps two local MCP concerns separate:

```text
agentic-security-applicability      # read-only analysis/applicability surface
agentic-security-governed-actions   # controlled mutable-action surface
```

For the governed mutable tool:

- `resource` and `environment` are untrusted tool arguments;
- `action` is fixed by the handler;
- the controlled local `caller_id` is injected by trusted server composition code;
- `caller_id`, `approval_id`, and `approver_id` are not tool arguments;
- tool annotations are metadata, not authorization;
- returned execution evidence is checked against a separate read-only state tool in the real STDIO smoke.

The local MCP experiment is intentionally not described as authenticated remote-user identity or production authorization.

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

The normal quality gate is provider-free. You do **not** need an LLM API key to validate the engineering contracts, tests, typing, architecture checks, security checks, governed-action behavior, MCP compatibility, or deterministic behavior.

For focused development:

```bash
uv run python scripts/quality_gate.py --list
```

For provider-backed experiments through LiteLLM, follow the [gateway foundation guide](docs/litellm/GATEWAY_FOUNDATION.md) and [final-evaluation methodology](docs/evaluation/FINAL_EVALUATION.md). Provider-backed final evaluation is intentionally separate from normal CI.

Read the full [development guide](docs/DEVELOPMENT.md) before changing framework adapters, authorization/runtime contracts, evaluation evidence, gateway policy, MCP tools, or telemetry contracts.

## Repository map

```text
src/agentic_lab/
├── domain/          # framework-neutral business concepts and invariants
├── application/     # use cases, evaluator/policy/authorization semantics, ports
└── adapters/        # LangGraph, CrewAI, LlamaIndex, Agno, gateway/action integrations

config/litellm/      # governed provider-access configuration
scripts/             # benchmarks, evaluation, quality gates, MCP servers/smokes
docs/                # architecture, ADRs, security, evaluation, MCP, privacy
artifacts/           # immutable benchmark/evaluation evidence
tests/               # provider-free regression, adversarial, conformance, and contract coverage
```

## Documentation map

### Understand the project quickly

- [Documentation by audience](docs/README.md)
- [Executive / portfolio overview](docs/EXECUTIVE_OVERVIEW.md)
- [Architecture and trust boundaries](docs/ARCHITECTURE.md)
- [Governed Agent Actions](docs/security/GOVERNED_AGENT_ACTIONS.md)
- [Framework decision matrix](docs/FRAMEWORK_DECISION_MATRIX.md)

### Build and change the code

- [Development guide](docs/DEVELOPMENT.md)
- [Engineering contract](AGENTS.md)
- [Agentic fast track](docs/AGENTIC_FAST_TRACK.md)

### Evaluate and reproduce evidence

- [Final-evaluation methodology](docs/evaluation/FINAL_EVALUATION.md)
- [Current five-way evidence](artifacts/final-evaluation/phase15-20260905-v2/benchmarks/comparison/five-way-latest.md)
- [Evaluation manifest](artifacts/final-evaluation/phase15-20260905-v2/manifest.json)
- [Governed-action cross-framework conformance](tests/integration/test_governed_action_framework_conformance.py)

### Security, privacy, and interoperability

- [Governed Agent Actions](docs/security/GOVERNED_AGENT_ACTIONS.md)
- [Privacy boundary](docs/PRIVACY.md)
- [Security experiments](docs/security/)
- [MCP overview](docs/MCP.md)
- [LiteLLM gateway foundation](docs/litellm/GATEWAY_FOUNDATION.md)
- [Architecture decision records](docs/adr/)

## What makes this a portfolio project rather than a framework demo

The repository is intentionally built around engineering decisions that survive framework replacement:

1. **Domain, policy, authorization, and enforcement stay framework-neutral.**
2. **Probabilistic output is validated by deterministic software.**
3. **A model can propose a mutable action but cannot authorize itself.**
4. **Failure behavior is observable instead of hidden.**
5. **Provider access is centralized behind a stable boundary.**
6. **Telemetry has an explicit privacy contract.**
7. **Benchmark evidence is persisted and tied to source state.**
8. **Trade-offs are documented instead of reduced to “framework X wins.”**

Those are the parts intended to be reusable when reasoning about enterprise agent platforms, AI gateways, governed runtimes, LLMOps, AI security, authorization, MCP, or framework selection.

## Project status

The planned **v1.0** engineering scope is complete: domain baseline, deterministic controls, RAG progression, four framework families / five orchestration variants, benchmark comparison, LiteLLM, MCP, observability, final evaluation, runtime hardening, and portfolio documentation.

Post-v1.0 development is extending the lab with **v1.1 Governed Agent Actions**: application-owned exact-scope authorization, trusted caller context, controlled HITL approval evidence, runtime enforcement, safe mutable execution, four-framework conformance, and a governed local MCP action boundary.

This remains an engineering lab, not a claim of production certification. Future work can extend identity, policy, approval durability, external side effects, and audit infrastructure without rewriting the accepted historical v1.0 evidence.

See [CHANGELOG.md](CHANGELOG.md) for release-level changes.
