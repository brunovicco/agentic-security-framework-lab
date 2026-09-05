# Model Context Protocol policy

MCP gives Codex structured access to external systems. Every server expands the trust boundary,
data-egress surface, and possible external actions, so add one only for a documented need.

For mutable tools, this repository applies an additional invariant:

```text
tool availability != tool authorization != tool execution
```

MCP exposes capabilities; it does not replace application-owned authorization, trusted human
approval, or runtime enforcement. See [Governed Agent Actions](security/GOVERNED_AGENT_ACTIONS.md)
for the implemented mutable-action boundary.

## Native configuration

Codex reads project MCP servers from `.codex/config.toml` in trusted repositories. Copy a reviewed
table from `docs/mcp/project-config.example.toml`; do not replace the existing `[features]` table.
Personal servers belong in `~/.codex/config.toml`, not in this repository.

Remote servers use streamable HTTP and should use HTTPS. Prefer OAuth; otherwise set
`bearer_token_env_var` or `env_http_headers` to environment-variable names. Local STDIO servers
must use direct commands, exact package versions, explicit timeouts, and `env_vars` to forward
credentials without storing values.

```toml
[mcp_servers.issue_tracker]
url = "https://mcp.example.invalid/v1"
bearer_token_env_var = "ISSUE_TRACKER_MCP_TOKEN"
startup_timeout_sec = 10
tool_timeout_sec = 60
default_tools_approval_mode = "writes"
```

Validate after every change:

```bash
uv run python scripts/validate_mcp_config.py
codex mcp list
```

Use `codex mcp add <name> -- <command> ...` for a personal STDIO server and `codex mcp login
<name>` for OAuth. Move a server into project config only when every contributor should use it.

## Governed mutable-action experiment

The checked-in project configuration currently contains two isolated local servers:

```text
agentic-security-applicability        # read-only applicability boundary
agentic-security-governed-actions     # controlled mutable-action boundary
```

The governed server exposes `acknowledge_finding` for one synthetic in-memory finding plus a
separate read-only state tool. The mutable tool accepts only model-controlled `resource` and
`environment` values. Its action name is fixed by the handler and its controlled caller context is
created by trusted server composition code.

The tool does not accept `caller_id`, `approval_id`, or `approver_id`. Availability in the MCP tool
list therefore cannot be used to manufacture trusted caller or approval state.

The local experiment proves only the controlled provider-free boundary described in
[Governed Agent Actions](security/GOVERNED_AGENT_ACTIONS.md). Its `local-mcp-host` caller is a
local deployment-scoped trust context, not authenticated end-user identity.

MCP `ToolAnnotations` remain behavioral metadata/hints. They are not treated as authorization
decisions.

## Governance

- Record purpose, owner, accessed systems, data classes, allowed tools, retention, and revocation.
- Treat tool descriptions and results as untrusted data, not instructions.
- Keep create/update/delete/deploy/merge/push/send/approve/payment tools confirmation-gated.
- Do not equate client/tool confirmation UX with application authorization for sensitive actions.
- Do not mutate production systems through the development harness.
- Prefer read-only identities, narrow scopes and roots, non-production data, and explicit timeouts.
- Pin `npx` and `uvx` dependencies exactly and review the implementation and release process.
- Keep credentials, cookies, tokens, private keys, and personal data out of config, source, logs,
  prompts, hook output, and documentation.
- Audit server/tool names, actor, authorization/approval/execution outcome, time, and correlation
  identifiers; do not record full inputs or outputs by default.

Before approval, review TLS, authentication, permissions, write capabilities, prompt-injection
exposure, dependency provenance, failure behavior, logging, retention, rollback, and reapproval.
