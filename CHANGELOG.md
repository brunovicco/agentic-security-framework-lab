# Changelog

## Unreleased

### Added

- Trusted caller identity provenance in `ActionContext`, distinguishing local composition from future authenticated identity mechanisms without letting model-controlled proposals declare either caller identity or provenance.
- A framework-neutral service-caller authentication contract that keeps opaque credentials separate from authorization and execution evidence.
- A provider-free static API-key authentication fixture that derives `identity_source = api_key` only after matching configured synthetic service credential verification material.

### Hardened

- Caller credentials use secret-safe representations, failed authentication produces no trusted `ActionContext`, and authentication decisions cannot carry contradictory context state.
- Configured synthetic API keys are reduced to SHA-256 digests in the controlled fixture and presented digests are compared with constant-time `hmac.compare_digest()`.

### Evidence

- Trusted-identity and service-authentication checks remain provider-free local/CI evidence and do not claim end-user authentication, OAuth/OIDC, remote MCP identity, or production secrets management.

## 1.1.0 - 2026-09-05

### Added

- Framework-neutral Governed Agent Actions contracts separating untrusted `ProposedAction` from trusted `ActionContext`.
- Exact least-privilege authorization over `(caller_id, action, resource, environment)` with fail-closed handling for unknown scopes.
- Runtime enforcement that treats `allow`, `deny`, and `require_human_approval` as explicit policy outcomes.
- Trusted human-approval evidence bound to the exact caller and action scope, with distinct `missing`, `invalid`, and `validated` states.
- Provider-free mutable-action integration using an in-memory finding acknowledgement adapter.
- Governed-action adapters for LangGraph, CrewAI Flow, LlamaIndex Workflow, and Agno Workflow, all delegating authority to the shared application runtime.
- Cross-framework conformance coverage comparing complete execution evidence and observable side effects with the direct application baseline.
- A separate governed mutable MCP STDIO server with compatibility and real host/client smoke checks.
- `docs/security/GOVERNED_AGENT_ACTIONS.md` documenting the v1.1 trust, authorization, HITL, enforcement, MCP, and evidence boundaries.

### Hardened

- Trusted HITL approvals are claimed as single-use capabilities so one approval cannot be replayed for repeated mutable executions; retries after a claimed approval require fresh human evidence.
- Mutable Agno Workflow execution disables framework retries so a failed side-effecting step is not silently retried.
- Model-adjacent proposals reject caller identity and approval-like extra fields rather than treating them as trusted authority.
- Governed MCP tools keep caller identity and approval authority outside model-controlled tool arguments.

### Evidence

- Governed-action application, framework-adapter, adversarial, conformance, and local MCP checks are provider-free CI evidence.
- The accepted v1.0 Phase 15 provider-backed evaluation artifacts remain immutable and are not rewritten by v1.1 work.
- The v1.1 work does not claim production certification, authenticated remote MCP identity, or provider-backed action execution.

## 1.0.0 - 2026-09-05

First portfolio-complete release of the Agentic Security Framework Lab.

### Added

- Framework-neutral Domain/Application contracts with framework adapters for LangGraph, CrewAI Agent/Crew, CrewAI Flow, LlamaIndex Workflow, and Agno Workflow.
- Deterministic validation, bounded semantic retries, oracle fallback, and human-review policy.
- Canonical five-framework evaluation and immutable Phase 15 final-evaluation evidence.
- Centralized LiteLLM gateway boundary using governed alias `security-analysis`.
- MCP 2026-07-28 / Python SDK v2 STDIO integration and real subprocess smoke coverage.
- Framework-neutral, content-free logical analysis observability with OpenTelemetry compatibility checks.
- Bilingual English/Portuguese portfolio landing pages, audience-based documentation navigation, executive overview, and expanded developer onboarding.

### Hardened

- CrewAI proprietary tracing disabled for final evaluation without disabling project-owned OpenTelemetry.
- LlamaIndex Workflow synchronous analysis offloaded from the event loop so the orchestration timeout remains responsive.
- LlamaIndex gateway request policy made explicit: 30-second request timeout, zero client-local retries, separate 45-second Workflow orchestration bound.

### Evidence

- Accepted final evaluation bundle: `artifacts/final-evaluation/phase15-20260905-v2/`.
- 75 framework executions produced 76 actual model calls and 100% expected final outcomes.
- Historical evaluation artifacts remain immutable; runtime-hardening commits after the accepted Phase 15 evidence do not rewrite that evidence.
