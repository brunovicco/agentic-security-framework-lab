# Governed mutable MCP actions

Phase 25 adds a second isolated MCP v2 STDIO server dedicated to mutable governed actions.

## Why a separate server

The original `agentic-security-applicability` server remains intentionally deterministic and read-only. The mutable experiment uses a separate server so the read-only Phase 13 evidence and attack surface stay unchanged.

The new server is `agentic-security-governed-actions` and exposes two Tools:

| Tool | Behavior | Purpose |
|---|---|---|
| `acknowledge_finding` | mutable, closed-world | propose one synthetic acknowledgement through the governed runtime |
| `get_finding_acknowledgement_state` | read-only, closed-world | independently verify observable local mutation |

## Trust boundary

```text
model / MCP client
       |
       | resource + environment
       v
acknowledge_finding Tool
       |
       | action fixed by adapter
       | caller context injected by composition root
       v
ProposedAction + ActionContext
       |
       v
GovernedActionRuntime
       |
       +-- allow ----------------------> in-memory executor
       |
       +-- deny -----------------------> no mutation
       |
       +-- require_human_approval
              |
              +-- approval missing ----> no mutation
```

The Tool input intentionally does **not** expose:

- `action`;
- `caller_id`;
- `approval_id`;
- `approver_id`.

`action` is fixed by the Tool adapter. `caller_id` is injected as `local-mcp-host` by the local composition root. Human approval remains a separate trusted application boundary.

## Least-privilege fixture policy

The synthetic server policy allows exactly one local scope:

```text
caller      = local-mcp-host
action      = acknowledge_finding
resource    = finding:demo-001
environment = test
outcome     = allow
```

The same caller/action/resource is explicitly denied in `staging` and requires human approval in `production`. Unknown resources or environments have no matching rule and therefore fail closed.

This makes Tool discovery deliberately broader than execution authority: a client can see the Tool even when the requested scope will be denied.

## Human approval

The server does not configure a trusted approval provider. Therefore the `production` rule returns:

```text
authorization.outcome = require_human_approval
approval_status       = missing
execution_occurred    = false
```

No MCP argument can manufacture approval. A later integration may connect a trusted approval provider, but that provider must remain outside model-controlled Tool arguments.

## Evidence

CI exercises the server in two ways:

1. an in-memory MCP v2 compatibility check validates Tool schemas, annotations, authorization outcomes, and observable state transitions;
2. a real STDIO host/client smoke launches the server from the committed `.codex/config.toml` and repeats blocked and allowed calls across the process boundary.

The expected sequence starts from an unacknowledged finding:

1. `staging` -> explicit deny -> state unchanged;
2. `production` -> human approval required/missing -> state unchanged;
3. unknown resource -> fail-closed deny -> state unchanged;
4. exact `test` scope -> allow -> state becomes acknowledged and execution count becomes one.

The separate state Tool prevents the transport proof from relying only on `ActionExecutionEvidence.execution_occurred`.

## What this does not prove

`local-mcp-host` is a local trusted composition value. It is **not authenticated remote identity**.

Phase 25 does not claim:

- remote Streamable HTTP readiness;
- OAuth or OIDC authentication;
- tenant/user identity propagation;
- durable state persistence;
- a production human-approval service;
- production authorization policy distribution;
- benchmark or provider behavior.

Those concerns remain separate increments.
