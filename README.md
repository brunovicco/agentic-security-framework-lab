# Agentic Security Framework Lab

[English](README.md) | [Português (Brasil)](README.pt-br.md)

[![quality](https://github.com/brunovicco/agentic-security-framework-lab/actions/workflows/quality.yml/badge.svg)](https://github.com/brunovicco/agentic-security-framework-lab/actions/workflows/quality.yml)

A framework-neutral engineering lab for building, securing, evaluating, and comparing **agentic AI systems** under the same deterministic controls.

The project implements the same vulnerability-analysis workload with **LangGraph, CrewAI, LlamaIndex, and Agno**, centralizes provider access with **LiteLLM**, validates reasoning outside the LLM, tests **MCP** compatibility, emits safe **OpenTelemetry** observations, and exercises **governed mutable actions** with caller authentication, identity-source-aware authorization, Human-in-the-Loop, approver authorization, and typed execution/failure evidence.

> **Core idea:** frameworks can own orchestration, but they should not automatically own security authority, policy, authorization, or final decisions.

## Why this project?

Agentic frameworks make prototypes easy. Systems closer to production need to answer harder questions:

- which controls should remain deterministic and framework-independent?
- how do we compare frameworks while keeping workload, expected truth, and policy constant?
- how can an agent propose an action without being able to authorize itself?
- how do we preserve evidence about *how* a result was produced?
- how do we separate identity, authorization, human approval, and execution?
- what should happen when a mutable executor fails after it has already been invoked?

This repository turns those questions into executable architecture, tests, benchmarks, and explicit trade-offs.

## Core invariant

```text
the LLM reasons
software validates
policy constrains
the runtime executes
evidence explains
```

For mutable actions:

```text
the agent/model proposes
trusted composition or authentication establishes caller context
policy authorizes
human approval is validated when required
approver policy validates reviewer authority
the runtime executes
evidence records success or governed failure
```

And one distinction remains explicit:

```text
tool availability != tool authorization != tool execution
```

See [Governed Agent Actions](docs/security/GOVERNED_AGENT_ACTIONS.md) for the complete trust model.

## What the project demonstrates

### Architecture and AI Engineering

- framework-neutral Domain and Application layers;
- LangGraph, CrewAI, LlamaIndex, and Agno adapters below stable contracts;
- structured output with deterministic post-validation;
- evaluator-optimizer with bounded retry and deterministic oracle fallback;
- LiteLLM as a provider-neutral boundary;
- explicit separation between application attempts and actual model calls;
- reproducible evaluation with immutable artifacts tied to exact commits.

### Security and governance

- `ProposedAction` is untrusted data; trusted `ActionContext` comes from outside model input;
- authentication and authorization are separate decisions;
- least-privilege authorization uses exact scope `(caller_id, identity_source, action, resource, environment)`;
- unknown scopes fail closed;
- approval is bounded, single-use, revocable before claim, and exact-scope within the controlled single-process provider;
- approver authority is checked separately;
- post-executor exceptions produce failure evidence with `execution_attempted=true` and `external_side_effect_state=unknown`;
- raw credentials and raw executor text are not copied into structured evidence;
- OpenTelemetry exports only safe metadata, not prompts, responses, rationale, evidence, or credentials.

### Platform and interoperability

- LangGraph `StateGraph` and evaluator-optimizer;
- CrewAI Agent/Task/Crew and CrewAI Flow;
- LlamaIndex Workflow;
- Agno Workflow with `max_retries=0` for the governed mutable action;
- MCP v2 with local STDIO smokes for read-only analysis, governed actions, and an authenticated experiment;
- cross-framework conformance against direct Application execution;
- provider-free CI for quality, typing, security, MCP, and OTel.

## Prompt injection stance

The project **does not claim to prevent or detect prompt injection**. It assumes an injection may influence model reasoning and asks: *what authority does that actually give the attacker?*

For mutable actions, an injection may influence `ProposedAction`, but it does not create caller identity, authorization, human approval, or approver authority by itself.

That does not mean every malicious proposal is blocked. If the proposal is already within authority legitimately granted to the caller and satisfies every required control, it can still execute. Least privilege, exact scope, and safe tool design therefore remain essential.

The repository's adversarial scenarios exercise specific parts of this boundary; they are not proof of broad prompt-injection resistance.

## Current governed runtime

The latest published release is **v1.3.0 — Human Approval Lifecycle**. Current `main` preserves the v1.1/v1.2/v1.3 contracts and includes later hardening for approver authorization, failure provenance, MCP uncertain execution, Agno error preservation, and cross-framework failure conformance.

The current boundary includes:

- `ProposedAction(action, resource, environment)` as untrusted proposal data;
- separate trusted `ActionContext(caller_id, identity_source)`;
- `allow`, `deny`, and `require_human_approval` outcomes;
- `HumanApprovalEvidence` with temporal validity and single-use claim in the single-process provider;
- approver authorization for `(approver_id, caller_id, identity_source, action, resource, environment)`;
- service-caller authentication before identity-source-aware authorization;
- `GovernedActionRuntime` as the single enforcement point before execution;
- `ActionExecutionEvidence`, `ActionExecutionFailureEvidence`, and authenticated variants;
- governed adapters for LangGraph, CrewAI Flow, LlamaIndex Workflow, and Agno Workflow;
- MCP treatment of uncertain post-executor failures as host-visible protocol errors rather than normal model-correctable Tool errors;
- exactly one executor attempt in the controlled failure scenario used by the conformance matrix.

This is **provider-free Application/framework/MCP integration evidence**. It is not a claim of production-grade IAM, remote OAuth/OIDC/JWT/mTLS identity, distributed approval, idempotency, rollback/compensation, an external PDP, tamper-proof evidence, or production certification.

## Declared architecture boundaries

Current limitations are explicit ADRs:

- [ADR 0009 — Tamper-evident execution evidence](docs/adr/0009-tamper-evident-execution-evidence.md): current evidence preserves in-memory provenance but does not prove a record was unchanged after creation.
- [ADR 0010 — Approval authority is single-process](docs/adr/0010-approval-authority-is-single-process.md): single-use, revocation, and temporal-validity guarantees currently hold within one process.
- [ADR 0011 — Uncertain external side effects](docs/adr/0011-uncertain-external-side-effects-idempotency-and-reconciliation.md): `external_side_effect_state=unknown` remains terminal in lab scope; idempotency/reconciliation are deferred until a real external executor exists.
- [ADR 0012 — External PDP boundary](docs/adr/0012-exact-scope-authorization-and-external-pdp-boundary.md): the exact in-process authorizer remains the reference; a future PDP must preserve the same authority semantics.

These ADRs document **boundaries and evolution criteria**, not already-implemented capabilities.

## v1.0 evaluation

Phase 15 compared five orchestration variants across the same five scenarios through the same LiteLLM boundary:

```text
Scenarios: 5
Repetitions per scenario: 3
Runs per variant: 15
Framework runs: 75
Actual model calls: 76
Evaluated commit: dd48c2490fc4ec1c76093577f7944d76a6fbc572
```

| Variant | Avg. tokens | Avg. latency | Avg. model calls | First-pass acceptance | Expected result |
| --- | ---: | ---: | ---: | ---: | ---: |
| LangGraph evaluator-optimizer | **611.33** | 3404.92 ms | 1.00 | 100% | 100% |
| CrewAI Agent + Task + Crew | 1136.60 | 2987.15 ms | 1.00 | 100% | 100% |
| CrewAI Flow + direct structured LLM | 630.60 | 3172.98 ms | 1.00 | 100% | 100% |
| LlamaIndex Workflow + `structured_predict()` | 732.20 | 3214.98 ms | **1.07** | **93.33%** | 100% |
| Agno Workflow + `Loop`/`Condition` | 632.00 | **2980.14 ms** | 1.00 | 100% | 100% |

All five reached the expected final result. The main finding is not “which framework won,” but that **execution path and cost changed while application-owned authority and policy remained constant**.

The LlamaIndex `product-mismatch` run required two rejected attempts before deterministic fallback, explaining why 75 runs produced 76 actual model calls.

These numbers do not establish statistical significance, production SLOs, or universal framework superiority.

Canonical evidence:

- [Phase 15 five-way report](artifacts/final-evaluation/phase15-20260905-v2/benchmarks/comparison/five-way-latest.md)
- [Evaluation manifest](artifacts/final-evaluation/phase15-20260905-v2/manifest.json)
- [Final evaluation methodology](docs/evaluation/FINAL_EVALUATION.md)

## Frameworks and authority

| Framework | Orchestration | Authorization/enforcement owner |
| --- | --- | --- |
| LangGraph | graph / `StateGraph` | `GovernedActionRuntime` |
| CrewAI | Agent/Crew and Flow | `GovernedActionRuntime` |
| LlamaIndex | Workflow | `GovernedActionRuntime` |
| Agno | Workflow / Step | `GovernedActionRuntime` |

Frameworks are adapters. The Application remains the owner of authorization, approval, and enforcement rules.

## MCP

The project keeps three local surfaces separate:

```text
agentic-security-applicability                  # read-only analysis
agentic-security-governed-actions               # mutable action through trusted composition
agentic-security-authenticated-governed-actions # isolated authenticated experiment
```

For mutable flows, `resource` and `environment` are untrusted inputs; caller identity, approval, and approver identity do not come from the Tool schema. Post-executor failures with uncertain side effects become host-visible `MCPError` failures without claiming that the external effect did not happen.

See [MCP](docs/MCP.md) for details.

## Quickstart

Requirements: Python 3.13 and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/brunovicco/agentic-security-framework-lab.git
cd agentic-security-framework-lab
uv sync --frozen --all-groups
uv run python scripts/quality_gate.py
```

The default quality gate runs without an LLM API key.

## Documentation

- [Executive overview](docs/EXECUTIVE_OVERVIEW.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Governed Agent Actions](docs/security/GOVERNED_AGENT_ACTIONS.md)
- [MCP](docs/MCP.md)
- [Framework decision matrix](docs/FRAMEWORK_DECISION_MATRIX.md)
- [Development guide](docs/DEVELOPMENT.md)
- [ADRs](docs/adr)
- [Complete documentation map](docs/README.md)

## Status

The planned **v1.0** engineering scope is complete. Published post-v1.0 releases are **v1.1 Governed Agent Actions**, **v1.2 Trusted Caller Identity**, and **v1.3 Human Approval Lifecycle**.

Current `main` includes later authorization, evidence, and MCP/framework hardening without rewriting historical artifacts or published releases.

This remains an **engineering lab**, not a claim of production certification.

See [CHANGELOG.md](CHANGELOG.md) for release-level changes.
