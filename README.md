# Agentic Security Framework Lab

[English](README.md) | [Português (Brasil)](README.pt-br.md)

[![quality](https://github.com/brunovicco/agentic-security-framework-lab/actions/workflows/quality.yml/badge.svg)](https://github.com/brunovicco/agentic-security-framework-lab/actions/workflows/quality.yml)

A framework-neutral engineering lab for building, securing, evaluating, and comparing **agentic AI workflows** under the same deterministic controls.

The project implements the same vulnerability-analysis workload with **LangGraph, CrewAI, LlamaIndex, and Agno**, routes provider access through **LiteLLM**, validates model reasoning outside the LLM, exposes **MCP** compatibility, emits logical **OpenTelemetry** observations without sensitive content, and exercises **governed mutable agent actions** through application-owned caller authentication, identity-source-aware authorization, bounded human approval, approver authorization, execution, and typed failure-evidence boundaries.

> **The core idea:** agent frameworks can own orchestration, but they should not automatically own security authority, policy, evidence, authorization, or final decisions.

## Why this project?

Agentic frameworks make prototypes easy, but production-grade AI systems face a harder set of questions:

- What happens when the model is wrong but the workflow still needs a safe result?
- Which controls should remain deterministic and framework-independent?
- How do retries, fallback, tool boundaries, telemetry, and provider access remain governable?
- How do different orchestration abstractions compare when the workload, expected truth, model-facing alias, and validation policy are held constant?
- How do we preserve evidence about *how* a result was produced instead of reporting only final accuracy?
- What happens when an agent can propose a mutable action but must not be able to authorize itself?
- How do caller identity, least privilege, human approval, and execution evidence remain stable when frameworks or tool surfaces change?

This repository turns those questions into executable architecture, tests, benchmark evidence, and explicit trade-offs.

## Reading guide

| Audience | Start here | What you can evaluate quickly |
| --- | --- | --- |
| **Developer/AI Engineer** | [Development guide](docs/DEVELOPMENT.md) → [Architecture](docs/ARCHITECTURE.md) | boundaries, typed contracts, adapters, retries, fallback, governed actions, MCP, OTel, reproducibility |
| **Engineering Manager/Architect** | [Executive overview](docs/EXECUTIVE_OVERVIEW.md) → [Governed Agent Actions](docs/security/GOVERNED_AGENT_ACTIONS.md) | governance model, authorization, provider boundary, operational trade-offs, framework portability, evidence discipline |
| **General audience** | this README → [Executive overview](docs/EXECUTIVE_OVERVIEW.md) | project scope, engineering ownership, technologies, measurable evaluation, AI-security and platform thinking |
| **Security/Governance** | [Architecture](docs/ARCHITECTURE.md) → [Governed Agent Actions](docs/security/GOVERNED_AGENT_ACTIONS.md) | trust boundaries, least privilege, HITL, runtime enforcement, adversarial tests, MCP, telemetry/privacy constraints |

See the [complete documentation map](docs/README.md).

## What the project demonstrates

### Architecture and AI engineering

- framework-neutral Domain and Application layers;
- framework adapters below stable application contracts;
- structured LLM output with deterministic post-validation;
- evaluator-optimizer control loops with bounded retry;
- deterministic oracle fallback when probabilistic reasoning is rejected;
- explicit separation between application analysis attempts and actual model calls;
- provider-neutral model access through a governed LiteLLM alias;
- suppression of framework-specific retries where hidden retries would distort evidence or multiply mutable side effects;
- immutable provider-backed evaluation artifacts tied to an exact Git commit;
- portable mutable-action orchestration across LangGraph, CrewAI, LlamaIndex, and Agno without moving authorization into those frameworks.

### Security and governance

- the LLM reasons over evidence but does not own the security-sensitive source of truth;
- evidence identity and applicability are validated outside the model;
- untrusted evidence has no instruction authority by default;
- deterministic policy controls human-review requirements;
- model-adjacent `ProposedAction` is separated from trusted `ActionContext`;
- caller authentication is a boundary separate from identity and authorization; raw credentials are not copied into trusted action context or execution evidence;
- exact least-privilege authorization evaluates `(caller_id, identity_source, action, resource, environment)` with no fallback across identity sources;
- unknown action scopes fail closed;
- `require_human_approval` remains blocked until separately sourced approval evidence is validated for the exact caller/action scope;
- approval authority is bounded, single-use, revocable before claim, time-limited, and source-isolated in the controlled **single-process** provider;
- approver authorization independently checks whether the trusted reviewer may approve exactly the requested scope;
- authorization, approval lifecycle, approver authorization, execution, and authentication are preserved as separate evidence facts;
- post-executor exceptions become typed governed failure evidence with `execution_attempted=true` and `external_side_effect_state=unknown`, without copying raw executor text into structured evidence;
- framework-owned telemetry is suppressed where relevant to preserve the project's privacy boundary;
- logical OpenTelemetry contains safe execution metadata, not prompts, responses, rationales, evidence, credentials, or provider payloads;
- provider/model mapping remains behind the gateway instead of leaking into each framework adapter.

### Platform and interoperability

- LangGraph evaluator-optimizer plus governed-action `StateGraph`;
- CrewAI Agent/Task/Crew;
- CrewAI Flow with direct structured LLM calls plus governed-action Flow;
- LlamaIndex Workflow with typed events plus governed-action Workflow;
- Agno Workflow with native loop/condition primitives plus a governed mutable Step with no retry;
- LiteLLM as the centralized provider-access boundary;
- MCP v2 compatibility plus real local STDIO host/client smokes for read-only applicability, trusted-composition governed actions, and a separate authenticated governed-action experiment with host-injected credentials;
- uncertain post-executor MCP failures are classified as host-visible protocol errors instead of model-correctable Tool errors;
- cross-framework governed-action conformance against the direct application runtime covers both normal execution states and typed executor-failure provenance;
- provider-free CI for quality, typing, security, MCP compatibility, governed mutable-action behavior, and OTel contract checks.

## Core invariant

```text
the LLM reasons
software validates
policy constrains
the runtime executes
evidence explains
```

The LLM is a probabilistic reasoning component, not the final authority.

For mutable actions, the same principle becomes:

```text
the agent/model proposes
trusted composition or authentication establishes caller context
policy authorizes
human evidence is claimed and validated when required
approver policy validates reviewer authority
the runtime enforces and executes
evidence records success or governed failure
```

And one distinction remains explicit throughout the project:

```text
tool availability != tool authorization != tool execution
```

See [Governed Agent Actions](docs/security/GOVERNED_AGENT_ACTIONS.md) for the complete current trust model.

## Prompt-injection stance

This project does not try to prevent prompt injection and does not claim to detect it.

It takes the opposite stance: assume the injection succeeded. Assume that untrusted evidence, a retrieved document, a tool description, or a manipulated asset identifier successfully influenced model reasoning. The architectural question is what that buys the attacker.

In read-only analysis, it buys a proposed conclusion that a deterministic evaluator checks against external evidence and rejects if wrong, with deterministic oracle fallback behind it.

For mutable actions, it buys a `ProposedAction` — untrusted proposal data. It does not buy caller identity, which is trusted context injected outside model-visible input. It does not buy an authorization decision, which is deterministic, exact, and identity-source-aware. It does not buy human approval evidence, which is separately sourced and bound to the exact caller and scope. It does not buy approver authority, which is checked independently. And it does not buy execution by itself, which only occurs after a single enforcement point has evaluated all of those facts.

A fully successful injection therefore **does not acquire additional authority by itself**. If the proposal is outside the authorized scope or requires approval evidence that does not exist, the runtime fails closed. If the proposal is already within authority legitimately granted to the caller and satisfies every required control, it can still execute — which is why least privilege, exact scope, and safe tool design remain essential even when the model is removed from the authority path.

The `adversarial-asset-id` scenario and the adversarial v2 document suite exercise this boundary at specific points. They are controlled tests, not proof of broad prompt-injection resistance — and under this threat model that is not what they are intended to prove. Detection is a mitigation. Removing the model from the authority path is a structural property, and that is what this repository is built around.

## Current governed-runtime snapshot — v1.1 through post-v1.3 hardening

The latest published release is **v1.3.0 — Human Approval Lifecycle**. Current `main` preserves the v1.1 governed-action contracts and v1.2 trusted-caller-identity contracts, adds the v1.3 approval lifecycle, and includes later hardening for approver authorization, typed executor-failure provenance, MCP uncertain-execution handling, and cross-framework failure conformance. These post-v1.3 changes are functionality of current `main`, not retroactive changes to the published v1.3 release.

The current controlled boundary includes:

- frozen `ProposedAction(action, resource, environment)` as untrusted proposal data;
- trusted, separate `ActionContext(caller_id, identity_source)` supplied by composition/runtime code or authentication;
- deterministic exact-scope authorization with `allow`, `deny`, and `require_human_approval` outcomes;
- trusted `HumanApprovalEvidence` bound to the exact proposal and caller context, with timezone-aware validity and single-use claim semantics in the controlled single-process provider;
- explicit approval outcomes for missing, revoked, invalid, unauthorized approver, not-yet-valid, expired, and validated states;
- separate approver authorization for exact scope `(approver_id, caller_id, identity_source, action, resource, environment)`;
- a service-caller authentication composition that establishes `api_key` caller context outside model/tool input, before identity-source-aware authorization;
- `GovernedActionRuntime` as the single enforcement point before mutable execution;
- `ActionExecutionEvidence` separating authorization, approval lifecycle, approver authorization, and execution itself;
- `ActionExecutionFailureEvidence` and `AuthenticatedActionExecutionFailureEvidence` for post-executor failure provenance without claiming whether an external side effect committed;
- a safe in-memory mutable finding-acknowledgement adapter;
- framework adapters for LangGraph, CrewAI Flow, LlamaIndex Workflow, and Agno Workflow;
- adversarial tests for caller spoofing, fake approvals, tool substitution, scope escalation, and retry after denial;
- cross-framework conformance comparing complete success/failure evidence and observable executor behavior with direct application execution;
- a governed mutable MCP STDIO server whose tool schema cannot provide trusted caller or approval identity;
- a separate authenticated MCP STDIO experiment with host-injected credentials whose raw credential remains outside model-visible tool arguments and structured evidence;
- MCP protocol-error classification for uncertain post-executor failures so an unknown side-effect state does not return through the normal model-correctable Tool-result channel;
- mutable Agno execution with `max_retries=0` and preservation of the original `GovernedActionExecutionError` through the framework's `RunStatus.error`.

The cross-framework conformance matrix covers exact allow, explicit deny, missing/validated approval, unauthorized approver, expired/revoked approval, caller mismatch, identity-source mismatch, resource escalation, and authorized executor failure. For every framework, normal execution evidence and post-executor failure evidence must match the direct application baseline, with exactly one executor attempt in the controlled failure scenario.

This is **provider-free Application/framework/MCP integration evidence**. It does not claim authenticated remote-user identity, OAuth/OIDC/JWT/mTLS, durable or distributed approvals, production-grade IAM/policy infrastructure, an external PDP, idempotency, rollback/compensation, provider-backed mutable execution, signed/tamper-proof audit evidence, or production certification.

## Declared architecture boundaries

The current contracts are intentionally small. The following limitations are not left as implicit omissions: they are recorded as accepted architecture decisions with a future design and explicit revisit triggers.

- [ADR 0009 — Tamper-evident execution evidence](docs/adr/0009-tamper-evident-execution-evidence.md): current evidence preserves execution facts and authority provenance in memory, but it **does not prove that a record was not altered after it was produced**. Evidence persistence is the trigger to revisit canonicalization, chaining, and signed checkpoints.
- [ADR 0010 — Approval authority is single-process](docs/adr/0010-approval-authority-is-single-process.md): single-use, revocation-before-claim, and temporal validity are guarantees of the current controlled provider **within one process**. Future distribution requires atomic claim semantics, fail-closed behavior under store unavailability, and real concurrency tests.
- [ADR 0011 — Uncertain external side effects: idempotency and reconciliation](docs/adr/0011-uncertain-external-side-effects-idempotency-and-reconciliation.md): `external_side_effect_state=unknown` remains terminal in lab scope. Idempotency keys, probes, and reconciliation become meaningful only when a real externally mutable executor exists.
- [ADR 0012 — Exact-scope authorization and the external PDP boundary](docs/adr/0012-exact-scope-authorization-and-external-pdp-boundary.md): the exact in-process authorizer remains the reference implementation. A future external PDP must preserve behavioral equivalence with the existing conformance matrix, including `identity_source` isolation and fail-closed behavior when the PDP is unavailable.

These ADRs document **boundaries and evolution criteria**, not already-implemented capabilities.

## v1.0 evaluation snapshot — cost and execution path under constant accuracy

The accepted Phase 15 evaluation runs five orchestration variants against the same scenario set through the same governed LiteLLM alias.

```text
Governed client alias: security-analysis
Scenarios: 5
Repetitions per scenario: 3
Runs per variant: 15
Framework runs: 75
Actual model calls: 76
Evaluated commit: dd48c2490fc4ec1c76093577f7944d76a6fbc572
```

All five orchestration variants reached the expected final result under the same application-owned controls. Accuracy is therefore constant in the comparison and is not a discriminator — it is the control condition, not the finding.

What changed was cost and execution path. The within-CrewAI comparison is the clearest case: `Agent + Task + Crew` and `Flow` solved the same workload within the same framework with materially different token envelopes in this sample. The LlamaIndex `product-mismatch` run is the other:

```text
LLM attempt 1 → rejected
LLM attempt 2 → rejected
deterministic oracle fallback → expected final result
```

That run is why 75 framework executions produced **76 actual model calls**, and it is the more useful of the two findings. A benchmark that reported only final accuracy would show five identical rows and hide the fact that one reached the result through a different path. The lab preserves that anomaly because evidence about recovery behavior is more valuable than a cosmetically uniform benchmark output.

| Variant | Average tokens | Average latency | Average model calls | First-pass acceptance | Expected final accuracy |
| --- | --- | --- | --- | --- | --- |
| LangGraph evaluator-optimizer | **611.33** | 3404.92 ms | 1.00 | 100% | 100% |
| CrewAI Agent + Task + Crew | 1136.60 | 2987.15 ms | 1.00 | 100% | 100% |
| CrewAI Flow + direct structured LLM | 630.60 | 3172.98 ms | 1.00 | 100% | 100% |
| LlamaIndex Workflow + `structured_predict()` | 732.20 | 3214.98 ms | **1.07** | **93.33%** | 100% |
| Agno Workflow + native `Loop`/`Condition` | 632.00 | **2980.14 ms** | 1.00 | 100% | 100% |

### What these numbers do not prove

- They do not establish statistical significance or production SLOs.
- Fifteen runs per variant are not enough for universal latency rankings.
- The results do not prove that any framework is generally superior.
- The adversarial scenarios are controlled tests, not proof of broad prompt-injection resistance.
- The `security-analysis` alias is a governed client identity, not an independent attestation of the native provider model selected behind the gateway.

Canonical evidence:

- [Phase 15 five-way report](artifacts/final-evaluation/phase15-20260905-v2/benchmarks/comparison/five-way-latest.md)
- [Machine-readable comparison](artifacts/final-evaluation/phase15-20260905-v2/benchmarks/comparison/five-way-latest.json)
- [Evaluation manifest](artifacts/final-evaluation/phase15-20260905-v2/manifest.json)
- [Final-evaluation methodology](docs/evaluation/FINAL_EVALUATION.md)

Historical provider-direct artifacts remain immutable and are intentionally not rewritten to reflect later gateway or runtime hardening.

## Framework implementations

### Analysis workload

| Framework/abstraction | Native orchestration | Structured reasoning path | Provider boundary | Deterministic authority |
| --- | --- | --- | --- | --- |
| LangGraph | graph nodes + conditional routing | LangChain structured output | LiteLLM `security-analysis` | Application |
| CrewAI Agent/Crew | `Agent` + `Task` + `Crew` | CrewAI structured output | LiteLLM `security-analysis` | Application evaluator |
| CrewAI Flow | Flow routing/state | direct structured `LLM.call()` | LiteLLM `security-analysis` | Application |
| LlamaIndex Workflow | typed Workflow events | `structured_predict()` | LiteLLM `security-analysis` | Application |
| Agno Workflow | `Workflow` + `Loop` + `Condition` | Agent structured output | LiteLLM `security-analysis` | Application |

### Governed mutable action

| Framework | Framework role | Trusted context | Authorization/enforcement owner |
| --- | --- | --- | --- |
| LangGraph | action node in the graph | injected outside graph input | `GovernedActionRuntime` |
| CrewAI Flow | deterministic Flow start | constructor dependency, outside Flow state | `GovernedActionRuntime` |
| LlamaIndex Workflow | typed-event step | constructor dependency, outside `StartEvent` | `GovernedActionRuntime` |
| Agno Workflow | custom Python Step | injected dependency, outside workflow input | `GovernedActionRuntime` |

The frameworks are deliberately adapters, not owners of business/security rules. See the [framework decision matrix](docs/FRAMEWORK_DECISION_MATRIX.md) for trade-offs observed in the analysis workload and [Governed Agent Actions](docs/security/GOVERNED_AGENT_ACTIONS.md) for the mutable-action boundary.

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

Framework clients know the stable alias and gateway contract. Native provider identifiers and provider credentials remain outside each framework-specific business path.

Separately, governed mutable actions use a different authority path:

```text
untrusted action proposal
     +
trusted caller context
     │
     ▼
application authorization
     │
     ├─ deny ──────────────────────► evidence/no execution
     │
     ├─ requires approval ─► trusted approval validation
     │                         │
     │                         └─ missing/invalid ─► no execution
     ▼
GovernedActionRuntime
     │
     ▼
mutable adapter
```

Application-owned logical telemetry describes safe analysis-execution facts without automatically exporting model content:

```text
Application execution
     │
     ▼
AnalysisExecutionObservation
     │ allowlisted safe attributes only
     ▼
deployment-owned OpenTelemetry composition
```

Read [Architecture](docs/ARCHITECTURE.md), [Governed Agent Actions](docs/security/GOVERNED_AGENT_ACTIONS.md), [LiteLLM gateway foundation](docs/litellm/GATEWAY_FOUNDATION.md), and [Privacy](docs/PRIVACY.md) for the detailed boundaries.

## MCP boundary

The project keeps versioned read-only and trusted-composition mutation concerns separate, plus an isolated authenticated experiment used by compatibility/smoke tests:

```text
agentic-security-applicability                  # read-only analysis/applicability surface
agentic-security-governed-actions               # trusted-composition mutable-action surface
agentic-security-authenticated-governed-actions # host-injected authenticated experiment; not project-registered
```

For the governed mutable tool:

- `resource` and `environment` are untrusted tool arguments;
- `action` is fixed by the handler;
- the controlled local `caller_id` is injected by trusted server composition code;
- `caller_id`, `approval_id`, and `approver_id` are not tool arguments;
- tool annotations are metadata, not authorization;
- returned execution evidence is cross-checked against a separate read-only state tool in the real STDIO smoke;
- the authenticated experiment receives synthetic credential material only from the trusted host/process environment and keeps it outside the Tool schema;
- after a governed executor has been invoked and raises, the trusted-composition and authenticated servers map only the typed governed failure into an `MCPError` protocol failure carrying safe evidence;
- this protocol classification prevents the uncertain side-effect state from becoming a normal model-visible `CallToolResult(is_error=true)` retry channel, but it does not prevent a host from implementing its own programmatic retry.

The local MCP experiments intentionally do not claim authenticated remote-user identity, transport-bound identity, production IAM, or production authorization. `external_side_effect_state=unknown` is preserved even when the controlled fixture observes zero mutation.

## Developer quick start

Requirements:

- Python 3.13
- [uv](https://docs.astral.sh/uv/)

```bash
git clone https://github.com/brunovicco/agentic-security-framework-lab.git
cd agentic-security-framework-lab
uv sync --frozen --all-groups
uv run python scripts/quality_gate.py
```

The normal quality gate runs provider-free. You **do not** need an LLM API key to validate the engineering contracts, tests, typing, architecture checks, security checks, governed-action behavior, MCP compatibility, or deterministic behavior.

For focused development:

```bash
uv run python scripts/quality_gate.py --list
```

For real-provider experiments through LiteLLM, follow the [gateway foundation guide](docs/litellm/GATEWAY_FOUNDATION.md) and [final-evaluation methodology](docs/evaluation/FINAL_EVALUATION.md). Provider-backed final evaluation is intentionally separate from normal CI.

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
- [Executive/portfolio overview](docs/EXECUTIVE_OVERVIEW.md)
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
- [Cross-framework governed-action conformance](tests/integration/test_governed_action_framework_conformance.py)

### Security, privacy, and interoperability

- [Governed Agent Actions](docs/security/GOVERNED_AGENT_ACTIONS.md)
- [Privacy boundary](docs/PRIVACY.md)
- [Security experiments](docs/security)
- [MCP overview](docs/MCP.md)
- [LiteLLM gateway foundation](docs/litellm/GATEWAY_FOUNDATION.md)
- [Architecture decision records](docs/adr)

## What makes this a portfolio project rather than a framework demo

The repository is intentionally built around engineering decisions that survive framework replacement:

1. **Domain, policy, authorization, and enforcement remain framework-neutral.**
2. **Probabilistic output is validated by deterministic software.**
3. **A model may propose a mutable action but cannot authorize itself.**
4. **Failure behavior is observable rather than hidden.**
5. **Provider access is centralized behind a stable boundary.**
6. **Telemetry has an explicit privacy contract.**
7. **Benchmark evidence is persisted and tied to source state.**
8. **Trade-offs are documented instead of being reduced to “framework X won.”**

These are the pieces intended to be reusable when reasoning about enterprise agent platforms, AI gateways, governed runtimes, LLMOps, AI security, authorization, MCP, or framework selection.

## Project status

The planned **v1.0** engineering scope is complete: domain baseline, deterministic controls, RAG progression, four framework families/five orchestration variants, benchmark comparison, LiteLLM, MCP, observability, final evaluation, runtime hardening, and portfolio documentation.

Published post-v1.0 milestones are **v1.1 Governed Agent Actions**, **v1.2 Trusted Caller Identity**, and **v1.3 Human Approval Lifecycle**. Current `main` additionally hardens approver authorization, governed executor-failure evidence, authenticated failure composition, MCP transport handling for uncertain execution, Agno failure-provenance preservation, and cross-framework failure conformance.

This remains an engineering lab, not a production-certification claim. Durable/distributed approval, transport-bound remote identity, production IAM, an external PDP, idempotency/rollback, external-side-effect transactionality, and signed/tamper-evident evidence infrastructure remain explicit non-goals until a concrete experiment requires them. Those boundaries are documented in [ADRs 0009–0012](docs/adr), including intended designs, limits on current claims, and revisit triggers. Historical provider-backed evidence and published release metadata are not rewritten by current-`main` hardening.

See [CHANGELOG.md](CHANGELOG.md) for release-level changes.