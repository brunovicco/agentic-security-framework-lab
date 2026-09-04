# MCP Phase 13

## Current foundation

Phase 13 targets MCP specification `2026-07-28` through the stable Python SDK v2 line.

The root framework-comparison environment still resolves MCP v1.x transitively through CrewAI, so MCP v2 runs in an isolated, exactly pinned process. ADR 0003 records that dependency boundary.

Current local topology:

```text
MCP host / client
      |
      | STDIO
      v
isolated MCP v2 server
      |
      +--> Resource: security://contracts/applicability
      |       |
      |       v
      |   application-controlled contract metadata
      |
      +--> Tool: assess_vulnerability_applicability
              |
              v
          application use case
              |
              v
          deterministic oracle
              |
              v
          domain version rules
```

## Why both a Tool and a Resource?

MCP primitives differ primarily by **who controls them**:

| Primitive | Controlled by | Current lab use |
|---|---|---|
| Tool | Model | Execute deterministic vulnerability applicability assessment |
| Resource | Application | Load the authoritative applicability contract schemas as context |
| Prompt | User | Not implemented yet |

A read-only tool is still a Tool. Its lack of side effects does not turn it into a Resource. The model may decide to invoke the applicability capability; the host/application decides whether to load the contract Resource into context.

## Resource design

`security://contracts/applicability` is intentionally static and application-controlled.

It does not copy fixture data or restate applicability rules. Instead, its content is generated from the same Pydantic models that define the application boundary:

- `VulnerabilityApplicabilityInput`;
- `AssetApplicabilityInput`;
- `ApplicabilityAssessmentResult`.

This makes schema evolution single-sourced. If the application contract changes, the Resource representation changes with it.

The Resource is labeled `application/json` and contains no credentials, external content, instructions, LLM output, or mutable state.

## Tool design

`assess_vulnerability_applicability` remains:

- deterministic for identical inputs;
- read-only;
- non-destructive;
- idempotent;
- closed-world;
- free of network, database, filesystem mutation, LLM, and provider credentials.

Its MCP annotations describe those properties for clients. They are metadata hints, not authorization controls. The implementation boundary is the security control.

## Compatibility evidence

CI validates two environments separately:

1. the root project quality gate under the locked framework-comparison dependency graph;
2. an isolated `mcp[cli]==2.1.1` environment that connects an MCP v2 `Client` to the server and exercises the actual protocol-facing Tool and Resource APIs.

The isolated check verifies catalog shape, Resource MIME/content, Tool annotations, and structured deterministic output.

## Deferred work

The following remain intentionally outside the current local foundation:

- Prompts;
- remote Streamable HTTP;
- OAuth / authorization policy;
- TLS and reverse-proxy topology;
- tenant or user identity propagation;
- remote resource protection metadata;
- MCP-specific observability;
- mutable or destructive tools;
- external/open-world resources.

Each introduces a separate security or governance concern and should be added only with focused tests and threat-model updates.

## References checked

- MCP `2026-07-28` release: https://blog.modelcontextprotocol.io/posts/2026-07-28/
- Python SDK v2 Resources: https://github.com/modelcontextprotocol/python-sdk/blob/main/docs/servers/resources.md
- Python SDK v2 first steps: https://github.com/modelcontextprotocol/python-sdk/blob/main/docs/get-started/first-steps.md
