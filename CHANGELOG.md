# Changelog

## Unreleased

### Added

- A framework-neutral `ActionApproverAuthorizer` independently decides whether the trusted `approver_id` named by claimed human evidence is entitled for the exact `(approver_id, caller_id, identity_source, action, resource, environment)` scope.
- `ActionExecutionEvidence` records approver authorization separately from caller authorization and approval lifecycle evidence.
- `ActionExecutionFailureEvidence` records the exact authority that permitted an executor invocation which raised, while fixing `execution_attempted=true`, `external_side_effect_state=unknown`, and `failure_reason=executor_error`.
- `GovernedActionExecutionError` carries safe failure evidence as a `RuntimeError` subtype and chains the original executor exception locally without copying raw executor error text into structured evidence.
- `AuthenticatedActionExecutionFailureEvidence` binds one successful caller-authentication decision to the exact governed executor-failure context it established.
- `AuthenticatedGovernedActionExecutionError` preserves authentication evidence across executor failure while remaining a subtype of `GovernedActionExecutionError` for existing catch behavior.

### Hardened

- Missing approver policy and unknown approver scope fail closed; trusted approval evidence no longer implies global approver authority.
- Claimed approval from an unauthorized approver is consumed, blocks before freshness or mutable execution, and is recorded as `unauthorized_approver`.
- Approver decisions and execution evidence reject contradictory outcome/reason or approval-status/approver-decision combinations.
- `AuthorizationDecision` now rejects caller outcome/reason pairs that deterministic policy cannot emit, including `allow` with a deny reason or `require_human_approval` without `human_approval_required`.
- `ActionExecutionEvidence` now validates the complete governed-action state machine: caller deny is terminal, direct allow is HITL-free and executed, and every HITL lifecycle state requires exactly the human evidence, approver decision, binding, and execution flag that the runtime can legally produce.
- Executor exceptions after an authorized direct or validated-HITL path no longer leave the authority chain unstructured; the runtime raises typed governed failure evidence without claiming that the external side effect committed or did not commit.
- Failed HITL executor attempts do not restore consumed approval authority, and structured failure evidence excludes raw executor exception content by construction.
- Authentication-first composition now re-wraps governed executor failures with the exact `credential_verified` evidence and rejects rejected-authentication or context-substitution combinations without copying credential or raw executor content.
- Authenticated MCP mutable execution now maps only post-executor `AuthenticatedGovernedActionExecutionError` states to host-visible `MCPError` protocol failures, preventing an uncertain side-effect outcome from becoming an ordinary model-visible Tool error that invites self-directed retry.
- The trusted-composition governed MCP mutable boundary now applies the same fail-closed transport classification to post-executor `GovernedActionExecutionError`, preserving safe action-level failure evidence while keeping raw executor text out of MCP protocol data.
- Agno governed mutable execution now preserves the original `GovernedActionExecutionError` across `RunStatus.error` instead of replacing application-owned failure provenance with a generic framework error; the existing `max_retries=0` boundary remains unchanged.

### Evidence

- Deterministic unit tests cover exact allow/deny, all six scope dimensions, default fail-closed behavior, runtime ordering, and evidence consistency.
- Adversarial coverage proves an exact, live approval from an unentitled reviewer causes zero side effects and cannot be replayed.
- Cross-framework conformance includes `unauthorized_approver`, proving direct runtime, LangGraph, CrewAI, LlamaIndex, and Agno preserve the same application-owned decision without framework-specific HITL policy.
- Approver authorization remains provider-free local/CI evidence; the lab does not claim human authentication, workforce IAM, signed approval attestation, role hierarchy, or multi-party approval.
- Evidence-model regressions enumerate every legal governed-action state and reject impossible combinations such as deny-plus-execution, allow-plus-HITL, mismatched `invalid` evidence, temporal states without approver allow, and `validated` without execution.
- This is structural evidence integrity only; it does not provide cryptographic signing, tamper-proof persistence, or transactional proof for an external side effect.
- Executor-failure regressions cover direct allow, validated HITL, consumed-approval retry, impossible failure-evidence authority states, raw-error exclusion, and an authorized missing-resource adapter failure whose original `LookupError` remains only as the local exception cause.
- Failure evidence deliberately reports the external side-effect state as `unknown`; the lab does not claim rollback, compensation, idempotent retry, two-phase commit, or distributed transaction semantics.
- Authenticated-failure regressions prove base-error compatibility, exact credential-derived context binding, rejected-credential short-circuiting, nested governed/original exception chaining, and absence of the raw API key from structured failure evidence.
- Exact isolated `mcp[cli]==2.1.1` compatibility and real STDIO checks prove uncertain authenticated mutable execution raises a protocol `MCPError`, not `CallToolResult(is_error=true)`, while preserving safe authenticated failure evidence in error `data`, zero observed fixture mutation for the failing resource, and a subsequent valid mutation.
- Governed trusted-composition MCP compatibility and real STDIO checks prove the same protocol-error boundary for action-level executor failure: safe `ActionExecutionFailureEvidence` remains in error `data`, the controlled failing resource shows zero observed fixture mutation without rewriting `external_side_effect_state=unknown`, and a subsequent valid mutation succeeds.
- The MCP protocol guard removes this failure class from the normal model-correctable Tool-result channel; it does not prove that every host will avoid programmatic retry and does not provide idempotency, rollback, compensation, or distributed transaction semantics.
- Agno failure regression coverage proves a mutable executor is attempted exactly once and callers receive the original governed failure evidence with exact context/action/authorization, `execution_attempted=true`, `failure_reason=executor_error`, and `external_side_effect_state=unknown`; raw executor text remains only in the local exception cause.

## 1.3.0 - 2026-09-05

### Hardened

- Human approval evidence now carries required timezone-aware `approved_at` and `expires_at` timestamps, with a positive validity window enforced at the evidence boundary.
- `GovernedActionRuntime` validates approval freshness against an application-owned trusted clock using the half-open interval `[approved_at, expires_at)`.
- Future-dated and expired approvals fail closed as `not_yet_valid` and `expired`; a claimed temporal failure remains consumed so retry requires fresh human evidence.
- Normal `allow` and terminal `deny` paths neither claim HITL evidence nor consult approval time.
- Approval claims now distinguish `missing`, `claimed`, and `revoked`, keeping absence, transferred authority, and withdrawn authority as separate runtime facts.
- Trusted control-plane code can revoke one exact still-unclaimed approval by immutable `approval_id`; revocation is sticky, blocks before freshness/execution, and cannot retroactively cancel an approval already claimed by a runtime attempt.
- The controlled approval provider now partitions claims by exact `(caller_id, identity_source, action, resource, environment)` scope, preventing one identity provenance from dequeuing approval authority issued for another provenance.
- Process-local approval claim and revocation transitions now share one synchronization boundary, making queue removal and lifecycle-state changes linearizable within one provider instance under concurrent callers.

### Evidence

- Deterministic runtime tests cover inclusive issuance, exclusive expiry, future-dated evidence, invalid clock output, anti-replay after temporal failure, and executor-failure semantics without sleeps or wall-clock-dependent tests.
- The adversarial suite proves an old unused approval cannot authorize a late mutable action, and cross-framework conformance proves expired approval semantics remain identical across the direct runtime, LangGraph, CrewAI, LlamaIndex, and Agno.
- Approval freshness and revocation evidence remain provider-free local/CI evidence; durable/distributed revocation, durable approval storage, multi-party workflow, and distributed transactional atomicity remain outside the current scope.
- Revocation regressions prove zero mutable side effects for revoked approval, sticky non-reuse on retry, and identical `revoked` semantics across direct runtime, LangGraph, CrewAI, LlamaIndex, and Agno.
- Source-confusion regressions prove an approval-gated request under the wrong identity source receives `missing` without consuming the correct-source approval, which remains available for the intended context and executes at most once.
- Concurrency regressions use barriers rather than sleeps to prove eight simultaneous claims transfer one approval exactly once, claim-vs-revoke races produce only linearizable outcomes, and eight concurrent approval-gated runtime attempts cause exactly one mutable execution.
- Approval concurrency evidence is process-local only; it does not prove cross-process/distributed atomicity or transactional coupling between approval state and external side effects.

## 1.2.0 - 2026-09-05

### Added

- Trusted caller identity provenance in `ActionContext`, distinguishing local composition from future authenticated identity mechanisms without letting model-controlled proposals declare either caller identity or provenance.
- A framework-neutral service-caller authentication contract that keeps opaque credentials separate from authorization and execution evidence.
- A provider-free static API-key authentication fixture that derives `identity_source = api_key` only after matching configured synthetic service credential verification material.
- An application-owned authenticated governed-action runtime that composes credential verification before authorization and passes only the derived `ActionContext` into the existing governed runtime.
- Source-aware least-privilege authorization over exact `(caller_id, identity_source, action, resource, environment)` scopes.
- A separate provider-free authenticated governed-action MCP v2 STDIO boundary that receives service credential material from trusted host/process environment rather than model-controlled Tool arguments.

### Hardened

- Caller credentials use secret-safe representations, failed authentication produces no trusted `ActionContext`, and authentication decisions cannot carry contradictory context state.
- Configured synthetic API keys are reduced to SHA-256 digests in the controlled fixture and presented digests are compared with constant-time `hmac.compare_digest()`.
- Rejected authentication cannot reach authorization or mutable execution, and authenticated execution evidence must use the exact context established by authentication.
- Identity-source mismatches fail closed with no legacy four-field fallback or cross-source authority inheritance; an `api_key` caller requires its own explicit policy rule instead of inheriting `trusted_composition` authority.
- The API-key fixture can be configured with precomputed SHA-256 verification material, and the authenticated MCP server removes the captured presented credential from its process environment before governed execution.
- Missing or invalid host credentials fail closed before mutable execution; credentials remain absent from Tool schemas and returned authentication/authorization/execution evidence.

### Evidence

- Trusted-identity, service-authentication, authentication-first runtime, source-confusion adversarial, and cross-framework source-aware conformance checks remain provider-free local/CI evidence and do not claim end-user authentication, OAuth/OIDC, remote MCP identity, or production secrets management.
- MCP v2 compatibility and real subprocess STDIO smoke checks prove host-injected service authentication for missing, invalid, denied, approval-required, and allowed paths while independently verifying zero side effects on blocked paths.

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
