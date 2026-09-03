# ADR 0002: Centralize LLM provider access behind LiteLLM Proxy

- Status: Accepted
- Date: 2026-09-03

## Context

The framework comparison milestone is complete. The lab now has framework adapters for LangChain/LangGraph, CrewAI, LlamaIndex, and Agno, but provider construction remains framework-specific:

- LangChain creates its own chat model;
- CrewAI creates its own `LLM`;
- LlamaIndex creates its own provider LLM;
- Agno creates its own provider model.

This was useful while learning each framework because it exposed each framework's native model integration. It becomes a liability once we want provider routing, retries, fallbacks, budgets, rate limits, cost tracking, or provider changes to behave consistently across frameworks.

If provider policy remains embedded in every adapter, a routing or provider change must be implemented repeatedly and can produce framework-specific behavior that is difficult to compare or govern.

## Decision

Introduce LiteLLM as a **central Proxy / LLM Gateway**, not as an embedded Python SDK inside each framework adapter.

Framework adapters will eventually call a stable gateway-facing model alias instead of selecting an upstream provider model directly.

The first alias is:

```text
security-analysis
```

The initial upstream mapping remains the model used by the accepted framework benchmark:

```text
security-analysis -> openai/gpt-5.6-luna
```

The mapping is infrastructure configuration. It is not part of the domain model.

The initial gateway configuration is intentionally minimal. Routing strategies, retries, fallbacks, budgets, virtual keys, and observability hooks will be introduced only when each behavior has an explicit testable policy.

## Why Proxy instead of embedded LiteLLM SDK

### Proxy / gateway

Advantages:

- one provider-access boundary for all frameworks;
- framework adapters can use a stable OpenAI-compatible endpoint;
- centralized authentication and future virtual-key policy;
- routing, cost controls, rate limits, and observability can evolve without importing those concerns into the domain;
- easier to compare framework orchestration separately from provider policy.

Costs:

- an additional runtime service;
- network hop and operational failure mode;
- gateway configuration becomes production-critical;
- health, timeout, and failover semantics must be designed explicitly.

### Embedded SDK

Advantages:

- fewer runtime components;
- simple local integration for one application;
- application-level routing can remain close to the caller.

Costs for this lab:

- every framework adapter would import or configure LiteLLM independently;
- provider policy would remain distributed;
- framework comparison would be contaminated by adapter-specific provider configuration.

The embedded SDK remains a valid architecture for a single Python application, but it does not fit this lab's platform-oriented comparison goal as well as a central gateway.

## Security consequences

- Provider credentials remain server-side and must be referenced through environment variables, never committed literally.
- The gateway master key must also come from the environment.
- A client-facing alias prevents callers from choosing arbitrary upstream provider identifiers by default.
- The gateway must fail closed when its committed configuration violates these invariants.
- Virtual keys and database-backed spend policy are deferred; adding them requires a separate security review because they introduce identity and persistence concerns.

## Consequences for framework adapters

This ADR does **not** migrate all frameworks immediately.

Migration will be incremental:

1. establish and validate the gateway configuration;
2. integrate one framework against the gateway while preserving the existing application contracts;
3. verify behavior and telemetry;
4. migrate the remaining frameworks one at a time;
5. only then introduce routing/fallback policies and compare their behavior.

## Alternatives rejected for now

### Keep direct provider integrations

Rejected because the project has reached the point where provider policy is duplicated across framework adapters.

### Build a custom gateway

Rejected because provider normalization, retry/fallback behavior, cost accounting, rate limits, and provider compatibility are not the learning objective of this repository. Reimplementing them would add substantial surface area without improving the framework-security comparison.

### Replace application ports with LiteLLM types

Rejected because LiteLLM is infrastructure. The domain and application layers must remain framework/provider neutral.
