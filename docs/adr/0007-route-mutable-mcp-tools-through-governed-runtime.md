# ADR 0007: Route mutable MCP Tools through the application-owned governed runtime

- Status: Accepted
- Date: 2026-09-05

## Context

The existing MCP v2 server exposes only deterministic read-only vulnerability applicability. Phase 25 introduces the first mutable MCP Tool in the lab.

A mutable Tool changes the security boundary. Tool discovery and Tool invocation are protocol capabilities, not authorization decisions. If an MCP handler can call a mutable executor directly, a client that reaches that Tool can bypass any policy enforced only in an upstream agent or framework.

The application already owns framework-neutral contracts for proposed actions, trusted caller context, deterministic authorization, trusted human approval evidence, runtime enforcement, and execution evidence.

A later hardening increment identified a transport-specific retry hazard after authenticated executor-failure evidence was introduced. Ordinary MCP Tool failures are returned through the Tool-result error channel used for model correction. That is appropriate for model-correctable input or Tool failures, but not for a mutable executor that has already been invoked when the external side-effect state is explicitly `unknown`. Returning that state as an ordinary Tool error can invite a model-directed retry of an operation that may already have committed.

## Decision

Expose mutable MCP capabilities only through a protocol adapter that constructs a `ProposedAction` and delegates to `GovernedActionRuntime` before the executor can mutate state.

```text
MCP client
    |
    v
mutable MCP Tool
    |
    | protocol input mapping only
    v
ProposedAction + trusted ActionContext
    |
    v
GovernedActionRuntime
    |
    +-- allow ----------------------> ActionExecutor
    |
    +-- deny -----------------------> blocked
    |
    +-- require_human_approval
           |
           +-- no trusted approval -> blocked
```

The first mutable Tool is intentionally narrow:

- Tool name: `acknowledge_finding`;
- action identity is fixed by the Tool handler and is not a Tool argument;
- model-controlled arguments are limited to `resource` and `environment`;
- caller identity is injected by the local server composition root as `local-mcp-host`;
- human approval identity or evidence is not accepted through Tool arguments;
- the existing fail-closed no-approval provider remains active, so production approval requirements cannot be satisfied by model input.

A second read-only Tool exposes the synthetic in-memory finding state so transport tests can verify side effects independently from the runtime's own `execution_occurred` field.

### Uncertain post-executor failure at the MCP boundary

For the host-authenticated mutable MCP server, only `AuthenticatedGovernedActionExecutionError` receives special transport handling. The Tool handler catches that error after the governed runtime has already recorded `execution_attempted=true` and `external_side_effect_state=unknown`, then raises a generic MCP protocol `MCPError` with `INTERNAL_ERROR`. Safe `AuthenticatedActionExecutionFailureEvidence` is serialized into protocol error `data`; raw host credentials and the raw executor exception message are not copied into that data.

This separates two transport meanings:

```text
model-correctable Tool error
    !=
uncertain mutable execution failure after executor invocation
```

The latter is rejected at the host/protocol boundary rather than returned as a normal `CallToolResult(is_error=true)`. Existing pre-executor paths are unchanged: caller deny, missing human approval, and invalid credentials continue returning their structured governed/authentication results; missing host credential remains the existing host-configuration Tool error.

This does not create a universal no-retry guarantee. A host can still choose to retry protocol errors in its own code. The boundary only prevents this uncertain mutable outcome from being delivered through the normal model-visible Tool-result error channel. No idempotency key, rollback, compensation, two-phase commit, or distributed transaction is introduced.

Phase 52 applies the same transport classification to the existing local trusted-composition governed server. It catches only `GovernedActionExecutionError`, maps it to `MCPError(INTERNAL_ERROR)`, and serializes safe `ActionExecutionFailureEvidence` under `data.execution_failure`. The application still owns authorization and failure semantics; this adapter mapping adds no policy and does not infer that a zero mutation observed in the controlled fixture changes the external side-effect state from `unknown`.

## Local caller identity

`local-mcp-host` is a trusted **composition value for this local lab process**. It is not proof that a remote user, model, agent, tenant, or client has authenticated as that identity.

This phase therefore proves policy binding to a caller dimension without claiming remote authentication or identity propagation. A later remote MCP increment must derive `ActionContext` from an authenticated boundary rather than reuse this local constant.

## Why authorization stays outside MCP semantics

MCP Tool annotations describe behavior for hosts and users. They do not replace application authorization.

Likewise, listing a Tool only proves that the server advertises a capability. It does not prove that the current caller and scope may execute it.

The server contains composition-time policy data for the synthetic experiment, but the authorization algorithm and enforcement semantics remain application-owned through `StaticActionAuthorizationPolicy` and `GovernedActionRuntime`.

## Security consequences

The adapter must preserve these properties:

- direct MCP Tool invocation still reaches `GovernedActionRuntime` before mutation;
- unknown resource or environment scopes fail closed;
- explicit deny cannot be overridden by Tool availability;
- `require_human_approval` has zero side effects when trusted approval is missing;
- caller identity cannot be spoofed through Tool arguments;
- approval identifiers cannot be supplied through Tool arguments;
- the Tool cannot substitute another action name;
- observable mutation is verified separately through a read-only state Tool.
- a post-executor failure whose external side-effect state is `unknown` is kept out of the normal model-visible Tool-result retry channel;
- MCP protocol failure data preserves safe authenticated governed evidence without raw credential or raw executor-error content.
- the trusted-composition governed variant preserves safe action-level failure evidence without raw executor-error content.

## Alternatives considered

### Authorize only in the agent or MCP client

Rejected because direct Tool invocation would become a bypass path around upstream policy.

### Put `caller_id` in the Tool schema

Rejected because model-controlled input must not choose the trusted principal used by authorization.

### Put approval data in the Tool schema

Rejected because human approval evidence is a separate trusted boundary. A model-provided boolean, approver name, or approval identifier is not trusted approval.

### Add the mutable Tool to the existing applicability server

Rejected because the existing server is intentionally read-only. A separate server keeps historical applicability evidence stable and makes the new mutable attack surface explicit.

## Consequences

Positive:

- MCP becomes another consumer of the same governed action runtime already used without MCP and through LangGraph;
- Tool availability remains distinct from authorization;
- local STDIO evidence can prove both blocked and successful mutations;
- the read-only Phase 13 server remains unchanged;
- no new root dependency is required because MCP v2 remains isolated.

Costs and limits:

- the local caller identity is static and not authenticated;
- mutable state is synthetic and process-local;
- no remote Streamable HTTP, OAuth, tenant propagation, persistence, or production approval service is introduced;
- application state persistence across server restarts is intentionally out of scope.

## Evidence classification

Phase 25 evidence is provider-free MCP v2 protocol-adapter integration evidence. It is not evidence of remote production readiness, authentication, durable persistence, or benchmark performance.

Phase 51 adds provider-free MCP v2.1.1 protocol-failure evidence for the authenticated local STDIO boundary: compatibility and real subprocess checks prove the uncertain post-executor path raises `MCPError`, carries safe structured failure `data`, produces no observed mutation in the controlled missing-resource fixture, and does not appear as a normal model-visible Tool error. This is not proof that an external side effect could not have partially or fully committed, nor that a host will never retry a protocol error.

Phase 52 extends that provider-free MCP v2.1.1 protocol-failure evidence to the trusted-composition governed STDIO boundary. Compatibility and real subprocess checks prove `GovernedActionExecutionError` arrives as `MCPError` with safe `ActionExecutionFailureEvidence`, not as a normal model-visible Tool error; zero observed fixture mutation remains separate from the runtime's deliberately `unknown` external side-effect state.
