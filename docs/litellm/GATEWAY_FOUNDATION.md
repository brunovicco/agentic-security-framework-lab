# LiteLLM Gateway Foundation

## Documentation Freshness Check

Checked on 2026-09-04:

- LiteLLM official Getting Started;
- LiteLLM official Proxy / LLM Gateway guidance;
- current official LiteLLM container package releases;
- LangChain `ChatOpenAI` integration and current API reference for custom `base_url` proxy clients;
- CrewAI v1.15.x LLM configuration for custom OpenAI-compatible endpoints;
- LlamaIndex `OpenAILike` integration for third-party OpenAI-compatible APIs;
- LlamaIndex structured prediction program selection based on function-calling metadata;
- PyPI dependency metadata for `llama-index-llms-openai-like==0.7.2`.

Current pattern considered:

- LiteLLM supports both a Python SDK embedded in an application and a central Proxy Server;
- the Proxy exposes an OpenAI-compatible API and centralizes provider access;
- proxy capabilities include authentication, spend tracking, rate limiting, logging hooks, and model routing;
- LangChain `ChatOpenAI` accepts an explicit `base_url` when the client talks to a proxy or service emulator;
- CrewAI `LLM` supports `custom_openai=True` with explicit `base_url` and `api_key` for OpenAI-compatible gateways;
- LlamaIndex provides `OpenAILike` specifically for third-party OpenAI-compatible APIs and explicit model capability metadata;
- LlamaIndex default structured prediction uses function calling when the LLM metadata advertises that capability;
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

CrewAI Agent/Crew and CrewAI Flow use the same client-facing gateway contract and have accepted compatibility-smoke evidence:

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

The current LlamaIndex client-migration increment uses its OpenAI-compatible integration while preserving the existing structured-prediction behavior:

```text
LlamaIndex Runtime / Workflow
    |
    v
LlamaIndex OpenAILike
    |
    | model = security-analysis
    | api_base = AGENTIC_LAB_GATEWAY_BASE_URL
    | chat = true
    | function calling = true
    v
LiteLLM Proxy
    |
    v
configured upstream provider model
```

LlamaIndex migration code is not accepted runtime evidence until a dedicated provider-backed gateway smoke is executed and reviewed. Agno remains on its direct provider integration during this transitional phase.

Framework orchestration, the shared `LLMAnalysisDraft` contract, deterministic validation, retry policy, fallback, and final result construction remain application-owned and unchanged. Only provider access is moving behind the gateway boundary.

## Why native framework clients instead of embedded LiteLLM

ADR 0002 selects LiteLLM as a central infrastructure service, not an in-process framework dependency.

For LangChain, the lab therefore uses `ChatOpenAI` with the proxy's OpenAI-compatible endpoint. For CrewAI, the lab uses CrewAI's native `LLM` custom OpenAI-compatible endpoint support rather than installing `crewai[litellm]` and introducing a second in-process LiteLLM layer. LlamaIndex uses its `OpenAILike` integration because the stable gateway alias is intentionally not an OpenAI provider model identifier.

This preserves the same architectural rule across frameworks:

- provider credentials and upstream model identifiers stay outside framework adapters;
- each migrated adapter knows only the stable gateway alias, endpoint, client credential, and capabilities required by its framework;
- LiteLLM remains independently deployable infrastructure;
- provider migration can occur behind the alias without changing domain/application code.

If a future experiment requires LiteLLM-specific in-process router behavior or provider-specific response extensions, that requires a separate architectural decision.

## LlamaIndex sampling and structured output

`OpenAILike` has its own default `temperature`, and its inherited OpenAI transport normally forwards that value with each request. The gateway adapter removes only that request parameter so sampling remains provider-owned, matching the existing LangGraph and CrewAI gateway policy.

The adapter explicitly advertises `is_chat_model=True` and `is_function_calling_model=True`. LlamaIndex uses the latter metadata when choosing the default Pydantic structured-prediction program, so this preserves the existing function-calling structured-output path instead of silently switching to text parsing.

The lab does not hard-code the configured upstream model's context window into the framework adapter. The current workload is intentionally small, and provider-specific capability policy belongs behind the governed alias rather than in domain/application code.

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

`AGENTIC_LAB_MODEL` no longer selects provider access for migrated LangGraph or CrewAI. Their post-migration runner metadata cleanup is complete. During the first LlamaIndex client-migration increment, historical direct-model inputs remain temporarily in runners/runtime construction even though the gateway alias selects provider access; issue #55 tracks their removal only after a provider-backed LlamaIndex smoke is accepted. Agno still uses `AGENTIC_LAB_MODEL` for direct provider selection until its own migration.

For post-migration runs, `security-analysis` identifies the governed alias actually requested by the client. It is not independent attestation of the provider model selected behind the proxy. The configured upstream remains gateway configuration evidence, and historical persisted benchmark artifacts are intentionally left unchanged.

## Why the committed config looks like JSON

`config/litellm/config.yaml` uses JSON syntax intentionally. JSON is valid YAML syntax, so the proxy configuration remains YAML-compatible while the repository can validate the initial security invariants with Python's standard library only.

This keeps the foundation validation provider-free and avoids adding a YAML/runtime dependency solely for configuration validation.

## Reading recommendation

Read these short sections when reviewing the gateway boundary:

1. LiteLLM Getting Started: **Proxy Server vs Python SDK**.
2. LangChain `ChatOpenAI` API reference: `base_url` and `api_key`.
3. CrewAI LLMs: **Custom OpenAI-Compatible Endpoint** and model-specific parameter guidance.
4. LlamaIndex `OpenAILike`: OpenAI-compatible API configuration and capability metadata.
5. LlamaIndex program utilities: default structured-prediction selection from `is_function_calling_model`.

Routing policies, virtual keys, budgets, observability callbacks, and gateway fallback remain deferred to dedicated increments.
