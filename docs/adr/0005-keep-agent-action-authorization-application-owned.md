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

## Evolution note: v1.1 Phases 19-22

Later increments preserved this decision while strengthening the exact authorization scope.

Phase 19 extended the static proof from action identity to exact `action + resource + environment` matching. Phase 22 adds caller identity as a fourth least-privilege dimension, but deliberately keeps that identity out of `ProposedAction`.

The application now carries trusted caller identity in a separate `ActionContext`. Static rules match exact `caller_id + action + resource + environment` tuples. This distinction is security-relevant because `ProposedAction` remains model-adjacent and untrusted: a model or evidence payload must not gain privileges by declaring its own caller identity.

This local `caller_id` is an authorization-context fixture, not proof of authentication and not a simulated IAM system. A future production boundary would need to derive the context from a genuinely trusted identity mechanism before invoking authorization.

Framework adapters may carry or close over this trusted context, but it must be supplied by the application boundary rather than generated as part of model intent.

The invariant is therefore:

```text
model intent != caller identity

ProposedAction = untrusted intent
ActionContext = trusted authorization context
```

## Evolution note: v1.2 Phase 34

Phase 34 makes the provenance of trusted caller identity explicit without claiming an authentication mechanism that the lab does not yet implement.

`ActionContext` now carries:

```text
caller_id
identity_source
```

The closed `CallerIdentitySource` initially permitted only `trusted_composition`. This value means that trusted application/composition code supplied the caller identity for the local execution boundary. It is provenance evidence, not proof that the caller was authenticated.

Authentication-like values such as `authenticated_principal` were intentionally unsupported until a real authentication boundary could derive caller context from verifiable identity evidence. Allowing arbitrary source strings would create the appearance of stronger trust without a mechanism that establishes it.

Because `ActionExecutionEvidence` already embeds the exact `ActionContext` used by authorization, identity provenance naturally becomes part of runtime evidence without adding a second identity channel.

`ProposedAction` continues to reject both `caller_id` and `identity_source`. MCP Tool schemas likewise keep those trusted fields outside model-controlled input.

The extended invariant is:

```text
model intent != caller identity != identity provenance != authorization decision
```

At Phase 34, `identity_source` was deliberately not a policy dimension because only one truthful trusted source existed. That constraint was temporary and explicitly intended to be revisited once a second genuinely established identity source existed.

## Evolution note: v1.2 Phase 37

Phases 35-36 introduced a second concrete identity source, `api_key`, and proved authentication-first composition before authorization. At that point, `caller_id` alone was no longer a sufficient least-privilege key: the same caller identifier could be established by materially different trust mechanisms.

Phase 37 therefore strengthens `StaticActionAuthorizationPolicy` to require exact rules over:

```text
(caller_id, identity_source, action, resource, environment)
```

There is no legacy four-field fallback and no cross-source inheritance. A rule for `trusted_composition` does not authorize the same caller when its context was established through `api_key`, and vice versa. If the exact five-field key is absent, the result remains fail-closed `deny / no_matching_rule`.

This change preserves the original application-owned authorization decision. Framework adapters and MCP still consume the same policy boundary; they do not interpret or synthesize source-specific authorization themselves. Existing local framework and MCP fixtures declare `trusted_composition` explicitly, while an authenticated `api_key` caller requires its own source-specific rule before execution can occur.

The source-aware invariant is:

```text
same caller_id != same authority when identity_source differs
```

This remains a small deterministic policy proof rather than a general ABAC language. There are still no wildcards, inheritance rules, external policy engine, or transport-specific authorization semantics.

## Revisit when

Revisit this decision if a later requirement demonstrates that policy ownership must move outside the application boundary, if resource/caller/source/environment rules require a dedicated policy representation or external engine, or when new authenticated identity mechanisms justify additional trusted identity-source values. Any replacement must preserve deterministic final authorization and keep framework adapters from becoming the source of authority.

Refs #117, #121, #127, #150, #156
