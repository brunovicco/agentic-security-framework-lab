# ADR 0007: Route mutable MCP Tools through the application-owned governed runtime

- Status: Accepted
- Date: 2026-09-05

## Context

The existing MCP v2 server exposes only deterministic read-only vulnerability applicability. Phase 25 introduces the first mutable MCP Tool in the lab.

A mutable Tool changes the security boundary. Tool discovery and Tool invocation are protocol capabilities, not authorization decisions. If an MCP handler can call a mutable executor directly, a client that reaches that Tool can bypass any policy enforced only in an upstream agent or framework.

The application already owns framework-neutral contracts for proposed actions, trusted caller context, deterministic authorization, trusted human approval evidence, runtime enforcement, and execution evidence.

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
