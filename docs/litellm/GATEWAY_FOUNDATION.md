# LiteLLM Gateway Foundation

## Documentation Freshness Check

Checked on 2026-09-04:

- LiteLLM official Getting Started;
- LiteLLM official Proxy / LLM Gateway guidance;
- current official LiteLLM container package releases;
- LangChain `ChatOpenAI` integration and current API reference for custom `base_url` proxy clients;
- CrewAI v1.15.20 LLM configuration for custom OpenAI-compatible endpoints.

Current pattern considered:

- LiteLLM supports both a Python SDK embedded in an application and a central Proxy Server;
- the Proxy exposes an OpenAI-compatible API and centralizes provider access;
- proxy capabilities include authentication, spend tracking, rate limiting, logging hooks, and model routing;
- LangChain `ChatOpenAI` accepts an explicit `base_url` when the client talks to a proxy or service emulator;
- CrewAI `LLM` supports `custom_openai=True` with explicit `base_url` and `api_key` for OpenAI-compatible gateways;
- sampling controls such as `temperature` are model-specific and are intentionally not forced by migrated clients;
- current official LiteLLM container releases include the v1.98.0 line.

Decision for this lab:

- use the central Proxy / LLM Gateway architecture;
- keep provider selection out of domain/application contracts;
- expose the stable client-facing alias `security-analysis`;
- initially map that alias to the same upstream model used by the accepted framework benchmark;
- migrate framework clients incrementally rather than changing all runtimes at once;
- defer retries, fallbacks, budgets, virtual keys, database-backed spend policy, and observability until each policy has its own tests.

## Current boundary

LangGraph is provider-backed through the gateway and has an accepted compatibility smoke:

```text
LangGraph
    |
    v
LangChain ChatOpenAI
    |
    | model = security-analysis
    | base_url = AGENTIC_LAB_GATEWAY_BASE_URL
    v
LiteLLM Proxy
    |
    v
configured upstream provider model
```

CrewAI Agent/Crew and CrewAI Flow now use the same client-facing gateway contract in code:

```text
CrewAI Agent/Crew or Flow
    |
    v
CrewAI LLM(custom_openai=True)
    |
    | model = security-analysis
    | base_url = AGENTIC_LAB_GATEWAY_BASE_URL
    v
LiteLLM Proxy
    |
    v
configured upstream provider model
```

The CrewAI client migration is not accepted runtime evidence until a provider-backed smoke is executed and reviewed. LlamaIndex and Agno still use their direct provider integrations during this transitional phase.

Framework orchestration, the shared `LLMAnalysisDraft` contract, deterministic validation, retry policy, fallback, and final result construction remain application-owned and unchanged. Only provider access is moving behind the gateway boundary.

## Why native framework clients instead of embedded LiteLLM

ADR 0002 selects LiteLLM as a central infrastructure service, not an in-process framework dependency.

For LangChain, the lab therefore uses `ChatOpenAI` with the proxy's OpenAI-compatible endpoint. For CrewAI, the lab uses CrewAI's native `LLM` custom OpenAI-compatible endpoint support rather than installing `crewai[litellm]` and introducing a second in-process LiteLLM layer.

This preserves the same architectural rule across frameworks:

- provider credentials and upstream model identifiers stay outside framework adapters;
- each adapter knows only the stable gateway alias, endpoint, and client credential;
- LiteLLM remains independently deployable infrastructure;
- provider migration can occur behind the alias without changing domain/application code.

If a future experiment requires LiteLLM-specific in-process router behavior or provider-specific response extensions, that requires a separate architectural decision.

## Shared client configuration

The client-facing gateway contract is centralized in `agentic_lab.adapters.gateway` and requires:

```text
AGENTIC_LAB_GATEWAY_BASE_URL
AGENTIC_LAB_GATEWAY_API_KEY
```

The gateway service itself owns provider-side configuration declared in `config/litellm/config.yaml`, including environment references for:

```text
OPENAI_API_KEY
LITELLM_MASTER_KEY
```

`AGENTIC_LAB_GATEWAY_API_KEY` is deliberately named as a client credential instead of reading `LITELLM_MASTER_KEY` directly. A local environment may temporarily assign the master key value to it, but the client contract can later receive a scoped virtual key without changing application code.

`AGENTIC_LAB_MODEL` no longer selects the model for migrated LangGraph or CrewAI provider access. LangGraph benchmark metadata has already been cleaned up to use the gateway alias. CrewAI runners still carry direct-model metadata temporarily so provider compatibility and benchmark metadata migration remain separate evidence increments; issue #48 tracks that cleanup after the CrewAI provider-backed smoke.

For post-migration runs, `security-analysis` identifies the governed alias actually requested by the client. It is not independent attestation of the provider model selected behind the proxy. The configured upstream remains gateway configuration evidence, and historical persisted benchmark artifacts are intentionally left unchanged.

## Why the committed config looks like JSON

`config/litellm/config.yaml` uses JSON syntax intentionally. JSON is valid YAML syntax, so the proxy configuration remains YAML-compatible while the repository can validate the initial security invariants with Python's standard library only.

This keeps the foundation validation provider-free and avoids adding a YAML/runtime dependency solely for configuration validation.

## Reading recommendation

Read these short sections when reviewing the gateway boundary:

1. LiteLLM Getting Started: **Proxy Server vs Python SDK**.
2. LangChain `ChatOpenAI` API reference: `base_url` and `api_key`.
3. CrewAI LLMs: **Custom OpenAI-Compatible Endpoint** and model-specific parameter guidance.

Routing policies, virtual keys, budgets, observability callbacks, and gateway fallback remain deferred to dedicated increments.
