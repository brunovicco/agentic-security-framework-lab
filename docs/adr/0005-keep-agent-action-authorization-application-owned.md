# ADR 0005: Keep agent action authorization application-owned and deterministic

## Status

Accepted

## Context

The v1.0 architecture separates probabilistic reasoning from deterministic validation, policy, fallback, and human-review decisions. Frameworks are orchestration adapters, and MCP is an interoperability boundary rather than a source of security authority.

v1.1 extends that model from governing analysis results to governing actions proposed by agents.

A tool being available to an agent does not imply that every invocation is authorized. Likewise, a model can propose an action, but model intent cannot be treated as evidence that the action is permitted.

The first authorization increment must establish this authority boundary without introducing framework-specific policy, MCP coupling, an external policy engine, or a simulated enterprise IAM system.

## Decision

Agent action authorization is owned by the application layer.

The application exposes:

- `ProposedAction` as an untrusted action proposal;
- `ActionAuthorizer` as the framework-neutral authorization port;
- `AuthorizationDecision` with the closed outcomes `allow`, `deny`, and `require_human_approval`;
- stable low-cardinality reason codes suitable for deterministic tests and future content-free telemetry;
- `StaticActionAuthorizationPolicy` as the first deterministic proof of the boundary.

The initial policy deliberately matches only exact action identity. It is not intended to be a complete RBAC or ABAC system. Resource, scope, environment, caller identity, risk, and approval evidence will be introduced only when a concrete later increment requires them.

When no authorization rule matches, the policy returns `deny` with `no_matching_rule`. Unknown authorization state therefore cannot become implicit permission.

`require_human_approval` is a distinct blocking outcome. It must not be interpreted as `allow`, and a later runtime-enforcement phase must prevent execution until valid approval exists.

Framework adapters and MCP boundaries may consume the application authorization contract later, but they must not redefine its policy semantics.

The project thesis therefore evolves without replacing the v1.0 rule:

```text
v1.0
LLM reasons
software validates
policy constrains
runtime executes
evidence explains

v1.1 extension
LLM proposes
software validates
policy authorizes
runtime enforces
evidence proves
```

## Alternatives considered

### Put authorization inside each agent framework

Rejected because it would duplicate security policy across LangGraph, CrewAI, LlamaIndex, and Agno and would allow framework choice to change the application authority model.

### Put authorization inside the MCP server

Rejected for the foundation because MCP is an interoperability mechanism. Making the server the primary policy owner would couple authorization semantics to one protocol before the application boundary is proven.

### Ask the LLM whether its proposed action is authorized

Rejected because the proposer cannot be the source of authority for its own permission. Model output may later contribute evidence, but a deterministic boundary must make the final authorization decision.

### Introduce an external policy engine now

Rejected because the first increment needs only to prove authority separation and fail-closed behavior. An external engine would add dependency, policy-language, deployment, and supply-chain complexity without solving a current requirement.

## Consequences

### Positive

- all future framework adapters can consume one authorization boundary;
- unknown actions fail closed deterministically;
- human approval remains distinguishable from permission to execute;
- policy reasons are stable and suitable for later audit/telemetry evidence;
- the first proof remains provider-free and dependency-free beyond existing application dependencies.

### Trade-offs

- action-only matching is intentionally coarse and does not yet prove least privilege across resource or environment scope;
- the policy is static and in-process, so it is not a general enterprise policy-management solution;
- runtime enforcement and action execution evidence remain separate follow-up increments.

These limitations are deliberate. Expanding the policy surface before runtime enforcement exists would increase model complexity without yet proving a stronger security control.

## Revisit when

Revisit this decision if a later requirement demonstrates that policy ownership must move outside the application boundary, or if resource/caller/environment rules require a dedicated policy representation or external engine. Any replacement must preserve deterministic final authorization and keep framework adapters from becoming the source of authority.

Refs #117
