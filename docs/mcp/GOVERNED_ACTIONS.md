# Governed mutable MCP actions

Phase 25 adds a second isolated MCP v2 STDIO server dedicated to mutable governed actions. Phase 34 strengthens its trusted caller evidence by making local identity provenance explicit without adding remote authentication claims.

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
       | caller context + provenance injected by composition root
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
- `identity_source`;
- `approval_id`;
- `approver_id`.

`action` is fixed by the Tool adapter. The local composition root creates trusted context as:

```text
caller_id       = local-mcp-host
identity_source = trusted_composition
```

`identity_source` describes the provenance of the caller identity used by the local experiment. It is not a model argument and is not proof that the caller was authenticated. Human approval remains a separate trusted application boundary.

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

`identity_source` is currently carried as trusted execution evidence rather than a policy dimension. There is only one truthful source in this local composition experiment, so source-aware authorization would add no meaningful distinction yet.

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

1. an in-memory MCP v2 compatibility check validates Tool schemas, annotations, trusted caller provenance, authorization outcomes, and observable state transitions;
2. a real STDIO host/client smoke launches the server from the committed `.codex/config.toml` and repeats blocked and allowed calls across the process boundary while verifying the same trusted caller provenance.

The expected sequence starts from an unacknowledged finding:

1. `staging` -> explicit deny -> state unchanged;
2. `production` -> human approval required/missing -> state unchanged;
3. unknown resource -> fail-closed deny -> state unchanged;
4. exact `test` scope -> allow -> state becomes acknowledged and execution count becomes one.

The separate state Tool prevents the transport proof from relying only on `ActionExecutionEvidence.execution_occurred`.

## What this does not prove

`local-mcp-host` with `identity_source = trusted_composition` is local trusted composition evidence. It is **not authenticated remote identity**.

Phase 34 still does not claim:

- remote Streamable HTTP readiness;
- OAuth or OIDC authentication;
- tenant/user identity propagation;
- an authenticated or federated identity source;
- durable state persistence;
- a production human-approval service;
- production authorization policy distribution;
- benchmark or provider behavior.

A future remote boundary must derive `ActionContext` from genuinely authenticated transport or application identity evidence. It must not expose `caller_id` or `identity_source` as model-controlled Tool arguments.
