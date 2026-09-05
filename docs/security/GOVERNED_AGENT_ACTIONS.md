# Governed Agent Actions

This document describes the v1.1 security model for **mutable agent actions** in the Agentic Security Framework Lab.

The goal is not to make an agent "trusted." The goal is to let an agent propose an action while keeping authorization, human approval, runtime enforcement, and execution evidence outside the model and outside framework-specific orchestration logic.

The central rule is:

```text
agent/model proposes
trusted context identifies the caller
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

It is frozen, rejects extra fields, and carries no trusted identity or human-approval state.

### Trusted execution context

`ActionContext` currently contains:

```text
caller_id
```

The caller context is supplied by trusted composition code. It is not accepted from `ProposedAction`, framework state controlled by the model, or MCP tool arguments.

This distinction prevents a proposal from upgrading itself by adding fields such as a privileged `caller_id` or fake approval metadata.

## 3. Deterministic authorization

`StaticActionAuthorizationPolicy` is the current controlled-lab policy implementation.

It evaluates an exact least-privilege key:

```text
(caller_id, action, resource, environment)
```

A rule can produce one of three outcomes:

- `allow`
- `deny`
- `require_human_approval`

There are no wildcards, role inheritance, nearest-match rules, or model-generated policy decisions in the current implementation.

If no exact rule exists, authorization fails closed with:

```text
outcome = deny
reason = no_matching_rule
```

This means changing only the resource, environment, caller, or action creates a different authorization request.

## 4. Human approval is separate authority

`require_human_approval` is not equivalent to `allow`.

When policy requires approval, `GovernedActionRuntime` asks an `ActionApprovalProvider` for trusted `HumanApprovalEvidence`.

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

## 5. Runtime enforcement

`GovernedActionRuntime` owns the enforcement order:

```mermaid
flowchart TD
    P[Untrusted ProposedAction] --> A[Deterministic authorization]
    C[Trusted ActionContext] --> A
    A -->|deny| D[Return evidence: no execution]
    A -->|allow| X[Execute adapter]
    A -->|require_human_approval| H[Resolve trusted approval evidence]
    H -->|missing or invalid| B[Return evidence: no execution]
    H -->|validated| X
    X --> E[Return execution evidence]
```

The executor is reached only after the application-owned control path permits it.

The runtime returns `ActionExecutionEvidence` containing independent facts about:

- the proposed action;
- trusted caller context;
- authorization decision and reason;
- approval status and approval evidence when present;
- whether execution occurred.

This distinction matters because:

```text
authorized != executed successfully
```

For example, policy can authorize a scope while the concrete executor can still fail because the target resource does not exist.

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
| resource escalation | fail-closed `deny` | none |

For every framework, the suite compares:

- the complete `ActionExecutionEvidence` object;
- observable in-memory state;
- successful execution count.

This is **provider-free cross-framework conformance evidence**. It does not prove production security, provider behavior, or statistical performance.

Relevant test:

- `tests/integration/test_governed_action_framework_conformance.py`

## 9. Adversarial boundary tests

Provider-free adversarial tests additionally exercise:

- escalation from a read-only caller to a mutable action;
- resource and environment escalation;
- privileged caller spoofing inside the untrusted proposal;
- fake approval-like fields inside the proposal;
- repeated denied attempts;
- tool/action substitution;
- unsafe proposals that must not imply unsafe side effects.

Relevant test:

- `tests/integration/test_adversarial_action_authorization.py`

These tests validate the implemented authorization boundary. They are not a claim of comprehensive prompt-injection, identity, or authorization-system coverage.

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
caller_id = local-mcp-host
```

The tool schema does not accept `caller_id`, `approval_id`, or `approver_id`.

The current local policy proves:

- exact `test` scope can execute;
- `staging` is explicitly denied;
- `production` requires approval and remains blocked because the local server does not configure an approval provider;
- resource substitution fails closed.

The compatibility and real STDIO smoke checks verify both returned execution evidence and independent observable state.

MCP tool annotations are treated only as behavioral metadata. They do not replace application authorization or runtime enforcement.

## 11. What the current implementation does not claim

This lab intentionally does not yet implement a general enterprise authorization platform.

Current non-goals include:

- RBAC/ABAC policy languages;
- wildcard or hierarchical resource scopes;
- authenticated end-user identity propagation;
- remote MCP OAuth authorization as proof of caller identity;
- durable approval workflows;
- approval expiry, revocation, or multi-party approval;
- transactional rollback for external side effects;
- distributed idempotency keys;
- production audit storage;
- external policy engines such as OPA/Cedar;
- proof of production isolation or certification.

The current `local-mcp-host` identity is a deployment-scoped local trust context for the experiment. It must not be described as authenticated user or agent identity.

## 12. Security invariants

The implemented v1.1 boundary is designed around these invariants:

1. **A model can propose an action but cannot authorize itself.**
2. **Tool discovery does not grant execution authority.**
3. **Caller identity is trusted context, not model-controlled proposal data.**
4. **Unknown scopes fail closed.**
5. **Human approval is separate trusted evidence, not a prompt field.**
6. **Approval is bound to one exact caller and action scope.**
7. **Framework adapters do not own policy or enforcement.**
8. **A denied or unapproved action must not reach the mutable executor.**
9. **Execution evidence is distinct from authorization evidence.**
10. **Framework-specific retries must not silently multiply mutable side effects.**

## 13. How to explain this in an interview

A concise explanation is:

> "The agent can propose a tool action, but the proposal is not authority. I keep caller identity in trusted runtime context, evaluate an exact least-privilege policy in the application layer, require separately sourced human approval when policy says so, and only then let the runtime call the mutable adapter. The same boundary is exercised through LangGraph, CrewAI, LlamaIndex, Agno, and MCP, so framework choice does not change the authorization semantics."

The important architectural point is not the specific in-memory action. It is that **orchestration remains replaceable while authorization and enforcement remain stable**.
