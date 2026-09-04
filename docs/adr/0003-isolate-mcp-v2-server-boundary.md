# ADR 0003: Isolate the MCP v2 server boundary from framework runtime dependencies

- Status: Accepted
- Date: 2026-09-04

## Context

Phase 12 centralized provider access behind LiteLLM and left the shared application/domain layers independent from framework-specific provider clients.

Phase 13 introduces Model Context Protocol (MCP) without changing that rule.

The current MCP specification is `2026-07-28`. Its protocol core is stateless, and the current stable Python SDK v2 line implements that revision. The project runtime, however, currently depends on CrewAI `1.15.18`, whose dependency graph remains on MCP SDK v1.x. Installing MCP v2 into the root project environment would therefore couple a protocol migration to a framework dependency conflict.

At the same time, implementing MCP with the older transitive SDK only because it is already present would make the new phase target a superseded protocol line.

## Decision

Run the MCP v2 server as a **separate STDIO process** using an exactly pinned ephemeral package environment:

```text
uvx --from "mcp[cli]==2.1.1" mcp run scripts/mcp_security_server.py
```

The project-scoped Codex configuration forwards only:

```text
PYTHONPATH=src
```

This allows the isolated MCP v2 process to import the repository's framework-neutral application/domain code without installing the root project dependency graph into that process.

The first server exposes one deterministic, read-only, closed-world tool:

```text
assess_vulnerability_applicability
```

The MCP adapter contains no vulnerability rule of its own. It delegates to the existing application-level deterministic oracle.

## Why STDIO first

STDIO keeps the first MCP increment focused on protocol and tool-boundary semantics:

- no listener or network exposure;
- no remote authentication or authorization design yet;
- no TLS, CORS, reverse proxy, service discovery, or deployment topology;
- one host launches one local child process;
- provider credentials are not involved.

Streamable HTTP remains the target for a later remote-server increment, where authorization, routing, and observability can be designed explicitly around the `2026-07-28` protocol.

## Why an ephemeral exact pin

The root environment remains reproducible under its existing lockfile and CrewAI dependency constraints. MCP v2 is resolved independently and exactly:

```text
mcp[cli]==2.1.1
```

The repository's MCP config validator accepts package extras only when the complete package requirement still uses an exact `==major.minor.patch` version. Floating versions and ranges remain rejected.

This gives the MCP service a versioned protocol boundary without weakening dependency discipline in the main runtime.

## Application boundary

The application layer owns the MCP-neutral input/output contract and deterministic use case:

```text
MCP host
    |
    | stdio
    v
MCP v2 protocol adapter
    |
    v
application.mcp_applicability
    |
    v
application.oracle
    |
    v
domain version rules
```

The MCP server is therefore an adapter in the same architectural sense as LangGraph, CrewAI, LlamaIndex, and Agno.

## Security consequences

The first tool is intentionally constrained:

- read-only;
- deterministic for the same inputs;
- no network access;
- no file mutation;
- no database access;
- no LLM call;
- no arbitrary tool dispatch;
- no provider credentials.

Its MCP `ToolAnnotations` declare `read_only_hint=true`, `destructive_hint=false`, `idempotent_hint=true`, and `open_world_hint=false`.

Those annotations are **metadata hints, not authorization controls**. Security depends on the actual implementation boundary remaining closed-world and side-effect free.

The committed host configuration contains no credentials. Future MCP servers that require authentication must use environment-variable forwarding and must pass the existing fail-closed MCP configuration validator.

## Alternatives considered

### Upgrade the root project to MCP v2 immediately

Rejected for this increment because the framework comparison environment still includes CrewAI with an MCP v1 dependency constraint. Overriding that constraint would make the root lockfile internally inconsistent and couple Phase 13 to an unrelated framework migration.

### Build Phase 13 on the transitive MCP v1 SDK

Rejected because this is a new implementation and should target the current stable MCP protocol and Python SDK line rather than intentionally starting on the legacy line.

### Duplicate the applicability rule inside the MCP server

Rejected because it would make the protocol adapter own business logic and create drift from the deterministic oracle already used by the framework-neutral application layer.

### Start with a remote Streamable HTTP server

Deferred. Remote transport is valuable, but it immediately introduces authorization, TLS, routing, deployment, and observability concerns. Those deserve their own threat model and tests rather than being hidden inside the first MCP increment.

## Consequences

Positive:

- MCP v2 can progress independently from CrewAI's MCP v1 dependency;
- the root lockfile does not change;
- application/domain code remains protocol neutral;
- the first MCP tool has a small attack surface;
- later MCP clients can consume the same deterministic capability.

Costs:

- the development host must resolve one exactly pinned ephemeral MCP CLI environment;
- the isolated process relies on the workspace source tree through `PYTHONPATH=src`;
- MCP v2 integration requires a separate compatibility check because the root test environment intentionally does not import the v2 SDK.

## References checked

- MCP specification release `2026-07-28`: https://blog.modelcontextprotocol.io/posts/2026-07-28/
- MCP Python SDK v2 documentation: https://github.com/modelcontextprotocol/python-sdk
- MCP Python SDK `2.1.1`: https://pypi.org/project/mcp/2.1.1/
