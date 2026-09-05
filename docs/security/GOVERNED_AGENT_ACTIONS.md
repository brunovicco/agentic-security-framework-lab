# Governed Agent Actions

This document describes the v1.1 security model for **mutable agent actions** and its v1.2 trusted-identity evolution in the Agentic Security Framework Lab.

The goal is not to make an agent "trusted." The goal is to let an agent propose an action while keeping caller authentication, identity provenance, authorization, human approval, runtime enforcement, and execution evidence outside the model and outside framework-specific orchestration logic.

The central rule is:

```text
agent/model proposes
trusted boundary establishes caller identity and provenance
policy authorizes
human evidence approves when required
runtime enforces
adapter executes
execution evidence proves what happened
```

A schema-valid tool call is therefore still only a proposal.

## 1. Why this boundary exists

Agent frameworks and MCP make tools easy to expose. Exposure is not authority.

The lab distinguishes three independent questions:

```text
Is the tool available?
        !=
Is this caller authorized for this exact action scope?
        !=
Did execution actually occur?
```

Collapsing those questions creates a dangerous failure mode: a model discovers a tool, selects it, and is implicitly treated as authorized to execute it.

The governed-action boundary prevents that collapse.

## 2. Trust model

Two inputs are deliberately separated.

### Untrusted proposal

`ProposedAction` contains model-adjacent action intent:

```text
action
resource
environment
```

It is frozen, rejects extra fields, and carries no trusted identity, identity provenance, credential, or human-approval state.

### Trusted execution context

`ActionContext` contains:

```text
caller_id
identity_source
```

The caller context is supplied by trusted application/composition code. It is not accepted from `ProposedAction`, framework state controlled by the model, or MCP tool arguments.

The currently implemented identity sources are:

```text
trusted_composition
api_key
```

`trusted_composition` means local trusted composition code supplied the identity. It remains provenance evidence rather than authentication proof.

`api_key` means the controlled service-caller authenticator verified a configured synthetic API key before creating the context. It is an authentication source for a service/client identity in this lab; it is not end-user identity and is not a replacement for OAuth/OIDC on a sensitive remote API.

Unsupported identity-source values remain rejected. This prevents code from labeling an identity with an authentication mechanism that the repository does not implement.

The trust relationship is therefore:

```text
model intent != caller authentication != caller identity != authorization decision
```

### Service-caller authentication boundary

Phase 35 introduces a separate framework-neutral authentication contract:

```text
CallerCredential
       |
       v
CallerAuthenticator
       |
       +-- rejected ------> no ActionContext
       |
       +-- authenticated -> trusted ActionContext
```

`CallerCredential` wraps the opaque credential with Pydantic `SecretStr`, so routine representations and JSON serialization mask the raw value.

`CallerAuthenticationDecision` contains only:

```text
outcome
reason
context | none
```

It does not retain credential material. The contract rejects contradictory evidence such as `authenticated` without context or `rejected` with trusted context.

The first provider-free adapter is `StaticApiKeyCallerAuthenticator`. It is intentionally a controlled fixture:

- configured synthetic high-entropy API keys are reduced to SHA-256 digests during construction;
- trusted composition can instead provide precomputed SHA-256 verification material, avoiding retention of an expected plaintext key before construction;
- the adapter retains digests and caller ids rather than configured plaintext keys;
- presented digests are compared with `hmac.compare_digest()`;
- an unknown credential returns `rejected` and no `ActionContext`;
- a successful match returns `identity_source = api_key`.

This fixture demonstrates the authentication boundary without claiming production secret storage, rotation, throttling, transport binding, or end-user authentication.

### Authentication-first governed execution

Phase 36 composes authentication with the existing governed runtime through `AuthenticatedGovernedActionRuntime`.

The application receives the credential and action proposal as separate inputs:

```text
CallerCredential + ProposedAction
        |
        v
AuthenticatedGovernedActionRuntime
        |
        +-- authentication rejected
        |       -> no ActionContext
        |       -> no authorization call
        |       -> no mutable execution
        |
        +-- authentication succeeds
                -> derived ActionContext only
                -> GovernedActionRuntime
                -> authorization
                -> approval when required
                -> execution when permitted
```

The credential itself is not forwarded into `GovernedActionRuntime`, the authorizer, the approval provider, or the executor.

`AuthenticatedActionExecutionEvidence` keeps two facts separate:

```text
authentication
execution | none
```

Rejected authentication must have no action execution evidence. Successful authentication must pair action execution evidence with the exact `ActionContext` produced by authentication. This prevents evidence from silently substituting a different caller after credential verification.

Authentication success is therefore a precondition for authorization, not a permission grant.

## 3. Deterministic authorization

`StaticActionAuthorizationPolicy` is the current controlled-lab policy implementation.

Phase 37 makes trusted identity provenance part of the exact least-privilege key:

```text
(caller_id, identity_source, action, resource, environment)
```

A rule can produce one of three outcomes:

- `allow`
- `deny`
- `require_human_approval`

There are no wildcards, role inheritance, nearest-match rules, model-generated policy decisions, or source fallbacks in the current implementation.

If no exact rule exists, authorization fails closed with:

```text
outcome = deny
reason = no_matching_rule
```

This means changing only the caller, identity source, action, resource, or environment creates a different authorization request.

Authentication and authorization remain separate. A successfully verified API key establishes caller context, but that context carries `identity_source = api_key` and must match an explicit API-key-specific authorization rule. A rule for the same `caller_id` under `trusted_composition` does not grant authority to the API-key context.

The source-aware invariant is:

```text
same caller_id != same authority when identity_source differs
```

There is deliberately no compatibility fallback to the older four-field key. Missing source-specific policy remains an unknown scope and therefore fails closed.

## 4. Human approval is separate authority

`require_human_approval` is not equivalent to `allow`.

When policy requires approval, `GovernedActionRuntime` asks an `ActionApprovalProvider` to **claim** trusted `HumanApprovalEvidence`.

Approval evidence is bound to the exact:

```text
ProposedAction + ActionContext
```

The runtime records one of these approval states:

- `not_applicable`
- `missing`
- `invalid`
- `validated`

Only validated, exact-match approval evidence can release an approval-required action for execution.

The default provider is fail-closed and returns no approval. The in-memory approval provider used by tests contains only explicitly supplied synthetic evidence; it never auto-approves.

### Approval anti-replay

Approval is modeled as a **single-use capability**, not a reusable boolean or lookup result.

`ActionApprovalProvider.claim_approval(...)` returns one unused approval at most once. The controlled in-memory provider removes a matching approval when it is claimed. A second identical request therefore receives `missing` unless a second, distinct human approval was supplied for that same scope.

The claim happens before the mutable executor runs. If the claimed evidence is invalid, or if the executor fails after the claim, the approval is not restored automatically. A retry requires fresh human approval.

This is deliberately fail-closed: a partially failed side effect must not make the same approval capability replayable.

The fixture rejects duplicate `approval_id` values and can hold multiple distinct approvals for the same exact scope when multiple executions were separately approved. This is process-local test evidence, not proof of durable or distributed transactional approval infrastructure.

## 5. Runtime enforcement

`GovernedActionRuntime` owns authorization, approval, and execution enforcement after trusted caller context exists:

```mermaid
flowchart TD
    P[Untrusted ProposedAction] --> A[Deterministic authorization]
    C[Trusted ActionContext] --> A
    A -->|deny| D[Return evidence: no execution]
    A -->|allow| X[Execute adapter]
    A -->|require_human_approval| H[Claim one unused trusted approval]
    H -->|missing or invalid| B[Return evidence: no execution]
    H -->|validated| X
    X --> E[Return execution evidence]
```

When service-caller authentication is used, `AuthenticatedGovernedActionRuntime` sits before this runtime and supplies the context only after credential verification succeeds.

The executor is reached only after the application-owned control path permits it.

The runtime returns `ActionExecutionEvidence` containing independent facts about:

- the proposed action;
- trusted caller context, including caller identity provenance;
- authorization decision and reason;
- approval status and approval evidence when present;
- whether execution occurred.

Because evidence embeds the same `ActionContext` used by authorization, the runtime does not create a second identity or provenance channel. Raw credentials are not part of `ActionContext`, `CallerAuthenticationDecision`, `ActionExecutionEvidence`, or `AuthenticatedActionExecutionEvidence`.

This distinction matters because:

```text
authenticated != authorized != executed successfully
```

For example, a service credential can authenticate successfully while policy still denies the requested action because its exact identity source has no matching rule. Likewise, policy can authorize a scope while the concrete executor can still fail because the target resource does not exist.

## 6. Safe mutable fixture

The controlled experiment uses `InMemoryFindingAcknowledgementExecutor`.

It exposes one synthetic mutable operation:

```text
acknowledge_finding
```

The fixture records observable acknowledgement state and a successful execution count. It also independently validates its own operation/resource invariants.

The fixture does **not** authorize the action. Authorization remains in the application layer.

Using an in-memory adapter keeps the experiment provider-free and prevents external side effects while still proving a real state transition.

## 7. Framework-neutral orchestration

The same `GovernedActionRuntime` is consumed by four orchestration frameworks.

| Framework | Orchestration primitive | Trusted context placement | Authorization owner |
| --- | --- | --- | --- |
| LangGraph | `StateGraph` node | injected outside graph input | Application |
| CrewAI | `Flow` + `@start()` | constructor dependency, outside Flow state | Application |
| LlamaIndex | `Workflow` + `StartEvent` / `StopEvent` | constructor dependency, outside event input | Application |
| Agno | `Workflow` + custom `Step` executor | injected dependency, outside workflow input | Application |

None of these adapters contains its own authorization rule table or interprets an authorization outcome to decide whether execution is permitted.

The framework orchestrates. The application decides and enforces.

Existing framework adapters continue to use their explicitly injected local `trusted_composition` context. Phase 37 migrates their policy fixtures to declare that source explicitly, so framework behavior cannot depend on an implicit source default inside authorization policy. API-key handling remains an application authentication concern rather than framework input.

### Agno retry hardening

The Agno mutable step explicitly uses `max_retries=0` and fail-closed step behavior.

This is security-relevant because an implicit framework retry around a mutating executor could multiply side effects after a partial failure.

A regression test uses a failing executor and proves it is invoked exactly once.

## 8. Cross-framework conformance

The integration conformance suite treats direct `GovernedActionRuntime` execution as the behavioral baseline and compares it with LangGraph, CrewAI, LlamaIndex, and Agno.

The controlled matrix covers:

| Scenario | Expected result | Side effect |
| --- | --- | --- |
| exact allow | `allow` | exactly one mutation |
| explicit deny | `deny` | none |
| approval required, approval missing | `require_human_approval` / `missing` | none |
| approval required, trusted approval present | `require_human_approval` / `validated` | exactly one mutation |
| caller mismatch | fail-closed `deny` | none |
| identity-source mismatch | fail-closed `deny` | none |
| resource escalation | fail-closed `deny` | none |

For every framework, the suite compares:

- the complete `ActionExecutionEvidence` object;
- observable in-memory state;
- successful execution count.

The identity-source mismatch scenario uses the same allowed caller and action scope but changes only the trusted context from `trusted_composition` to `api_key`. Because no API-key-specific rule exists in that fixture, the direct runtime and all four framework adapters must return `deny / no_matching_rule` with zero side effects.

This is **provider-free cross-framework conformance evidence**. It does not prove production security, provider behavior, remote identity propagation, or statistical performance.

Relevant test:

- `tests/integration/test_governed_action_framework_conformance.py`

## 9. Adversarial boundary tests

Provider-free adversarial tests additionally exercise:

- escalation from a read-only caller to a mutable action;
- identity-source substitution for the same caller and action scope;
- resource and environment escalation;
- privileged caller spoofing inside the untrusted proposal;
- fake approval-like fields inside the proposal;
- repeated denied attempts;
- trusted approval replay after one successful mutable execution;
- tool/action substitution;
- unsafe proposals that must not imply unsafe side effects.

Identity tests additionally prove that model-adjacent proposals cannot smuggle `identity_source`, unsupported provenance values are rejected, an invalid service credential creates no trusted context, rejected authentication cannot reach authorization or mutable execution, and an API-key context does not inherit a trusted-composition rule.

Relevant tests:

- `tests/integration/test_adversarial_action_authorization.py`
- `tests/integration/test_governed_action_framework_conformance.py`
- `tests/unit/application/test_action_authorization.py`
- `tests/unit/application/test_action_identity.py`
- `tests/unit/application/test_authenticated_action_runtime.py`
- `tests/unit/adapters/test_service_caller_authenticator.py`

These tests validate the implemented authorization and authentication boundaries. They are not a claim of comprehensive prompt-injection, enterprise IAM, or authorization-system coverage.

## 10. MCP governed mutable action

The repository keeps the original read-only applicability MCP server and the governed mutable-action MCP server separate.

Project configuration exposes:

```text
agentic-security-applicability
agentic-security-governed-actions
```

The governed server exposes a mutable `acknowledge_finding` tool plus a separate read-only state tool used to observe the resulting side effect.

The mutable tool accepts only:

```text
resource
environment
```

The action name is fixed by the handler as `acknowledge_finding`, and the controlled local caller context is created by the server composition root as:

```text
caller_id       = local-mcp-host
identity_source = trusted_composition
```

The tool schema does not accept `caller_id`, `identity_source`, credentials, `approval_id`, or `approver_id`.

The current local policy binds every MCP rule explicitly to `identity_source = trusted_composition` and proves:

- exact `test` scope can execute;
- `staging` is explicitly denied;
- `production` requires approval and remains blocked because the local server does not configure an approval provider;
- resource substitution fails closed;
- another identity source cannot inherit the local composition rules.

The compatibility and real STDIO smoke checks verify both returned execution evidence, including trusted identity provenance, and independent observable state.

MCP tool annotations are treated only as behavioral metadata. They do not replace application authorization or runtime enforcement.

### Host-injected authenticated STDIO boundary

Phase 38 adds a separate provider-free MCP v2 STDIO server for authenticated governed actions. It is intentionally not registered in project `.codex/config.toml`: authentication material belongs to the trusted host/process environment rather than model-visible Tool arguments or checked-in server configuration.

The host supplies two separate values to the subprocess environment: a presented synthetic service credential and precomputed SHA-256 verification material. The server captures the presented credential, removes that raw value from the process environment, constructs `CallerCredential`, and invokes `AuthenticatedGovernedActionRuntime`.

The model-visible mutable Tool still accepts only:

```text
resource
environment
```

It cannot supply `credential`, `api_key`, `caller_id`, `identity_source`, `approval_id`, or `approver_id`. The authenticated context is created only after credential verification and carries:

```text
caller_id       = local-api-key-client
identity_source = api_key
```

The exact source-aware policy then independently decides the action. Real subprocess STDIO smoke coverage proves three isolated host cases:

- missing presented credential -> fail-closed Tool error and zero observable mutation;
- invalid presented credential -> `rejected / credential_rejected`, no execution evidence, and zero observable mutation;
- valid presented credential -> authentication succeeds, while `staging` is still denied, `production` still requires missing human approval, and only exact `test` scope executes.

A separate read-only state Tool verifies mutation independently after each path. Smoke credentials are generated at runtime, the expected plaintext credential is not committed, and the raw presented credential is not included in returned authentication, authorization, or execution evidence.

This proves local host-injected service authentication across a real MCP v2 STDIO subprocess. It does not prove remote MCP identity propagation, transport-bound authentication, OAuth/OIDC/JWT/mTLS, production secret management, or end-user identity.

## 11. What the current implementation does not claim

This lab intentionally does not yet implement a general enterprise authorization or identity platform.

Current non-goals include:

- RBAC/ABAC policy languages;
- wildcard or hierarchical resource scopes;
- identity-source wildcards or inheritance;
- authenticated end-user identity propagation;
- remote MCP OAuth authorization as proof of caller identity;
- federated identity or OIDC/JWT validation;
- password authentication;
- API-key rotation, expiry, throttling, or vault integration;
- transport-bound service authentication;
- durable approval workflows;
- approval expiry, revocation, or multi-party approval;
- distributed transactional atomicity between approval claims and external side effects;
- transactional rollback for external side effects;
- distributed idempotency keys;
- production audit storage;
- external policy engines such as OPA/Cedar;
- proof of production isolation or certification.

The current MCP `local-mcp-host` identity with `identity_source = trusted_composition` is a deployment-scoped local trust context for the experiment. It must not be described as authenticated user or agent identity.

The `api_key` source proves only a matching synthetic service credential in the controlled fixture. Phase 38 additionally proves local host-injected authentication across a real MCP v2 STDIO subprocess, while still making no claim of remote authenticated identity propagation or transport-bound authentication.

## 12. Security invariants

The implemented Governed Agent Actions boundary is designed around these invariants:

1. **A model can propose an action but cannot authorize itself.**
2. **Tool discovery does not grant execution authority.**
3. **Caller identity is trusted context, not model-controlled proposal data.**
4. **Identity provenance is trusted context and cannot be declared by the model.**
5. **Credential verification is separate from action authorization.**
6. **Failed authentication produces no trusted `ActionContext`.**
7. **Failed authentication cannot reach authorization, approval, or mutable execution.**
8. **Raw caller credentials do not enter authorization or execution evidence.**
9. **Authenticated execution must use the exact context established by authentication.**
10. **Authentication success never implies action authorization.**
11. **`trusted_composition` provenance is not authentication proof.**
12. **`api_key` identifies only the controlled service credential mechanism.**
13. **Authorization binds to exact caller identity provenance as well as action scope.**
14. **The same `caller_id` does not inherit authority across identity sources.**
15. **Unknown or source-mismatched authorization scopes fail closed.**
16. **Human approval is separate trusted evidence, not a prompt field.**
17. **Approval is bound to one exact caller context and action scope.**
18. **One claimed approval cannot be replayed for a second mutable execution.**
19. **A retry after a claimed approval requires fresh human evidence.**
20. **Framework adapters do not own policy or enforcement.**
21. **A denied or unapproved action must not reach the mutable executor.**
22. **Execution evidence is distinct from authorization evidence.**
23. **Framework-specific retries must not silently multiply mutable side effects.**
24. **Host credential material is separate from model-controlled MCP Tool input.**
25. **Missing or rejected host authentication cannot produce mutable side effects.**
26. **Local STDIO host injection must not be described as remote or transport-bound authentication.**

## 13. How to explain this in an interview

A concise explanation is:

> "Once I had two trusted identity sources, caller ID alone stopped being a sufficient authorization key. I kept authentication separate: a credential first derives a trusted `ActionContext`, then authorization matches the exact caller, identity source, action, resource, and environment. There is no cross-source fallback, so an API-key-authenticated caller does not inherit authority granted to the same caller ID under local trusted composition. At the MCP boundary, the host injects credential material outside the Tool schema, so the model still proposes only action scope. Failed authentication never reaches policy, successful authentication can still be denied, human approval remains a separate authority, and the same runtime semantics hold across LangGraph, CrewAI, LlamaIndex, Agno, and MCP."

The important architectural point is not the specific in-memory action or synthetic credential. It is that **authentication, identity provenance, authorization, approval, and execution are independent control points rather than one model-controlled tool call**.
