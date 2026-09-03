# LiteLLM Gateway Foundation

## Documentation Freshness Check

Checked on 2026-09-03:

- LiteLLM official Getting Started;
- LiteLLM official Proxy / LLM Gateway guidance;
- current official LiteLLM container package releases;
- LangChain `ChatOpenAI` integration and current API reference for custom `base_url` proxy clients.

Current pattern considered:

- LiteLLM supports both a Python SDK embedded in an application and a central Proxy Server;
- the Proxy exposes an OpenAI-compatible API and centralizes provider access;
- proxy capabilities include authentication, spend tracking, rate limiting, logging hooks, and model routing;
- LangChain `ChatOpenAI` accepts an explicit `base_url` when the client talks to a proxy or service emulator;
- `ChatOpenAI` targets the standard OpenAI API contract and does not preserve provider-specific response extensions;
- current official LiteLLM container releases include the v1.98.0 line.

Decision for this lab:

- use the central Proxy / LLM Gateway architecture;
- keep provider selection out of domain/application contracts;
- expose the stable client-facing alias `security-analysis`;
- initially map that alias to the same upstream model used by the accepted framework benchmark;
- migrate framework clients incrementally rather than changing all runtimes at once;
- defer retries, fallbacks, budgets, virtual keys, database-backed spend policy, and observability until each policy has its own tests.

## Current boundary

The first client migration routes the LangGraph workload through LangChain's standard OpenAI-compatible client:

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
openai/gpt-5.6-luna
```

LangGraph orchestration, the shared `LLMAnalysisDraft` contract, deterministic validation, retry policy, fallback, and final result construction are unchanged. Only provider access moved behind the gateway boundary.

CrewAI, LlamaIndex, and Agno still use their direct provider integrations during this transitional increment. Their migration will be reviewed separately so framework behavior remains attributable and testable.

## Why `ChatOpenAI` instead of embedding LiteLLM in the adapter

LangChain also offers integrations for applications that want to use LiteLLM as an in-process Python library. That is not the architecture selected by ADR 0002.

This lab intentionally uses `ChatOpenAI` with the proxy's OpenAI-compatible endpoint because:

- LiteLLM remains a central infrastructure service rather than a framework dependency;
- provider credentials and upstream model identifiers stay outside the LangChain adapter;
- the adapter only knows a stable model alias and transport endpoint;
- the existing `BaseChatModel` boundary remains unchanged;
- we do not currently depend on non-standard provider response fields.

If a future experiment requires LiteLLM-specific in-process router behavior or provider-specific response extensions, that would be a separate architectural decision rather than an accidental dependency introduced by this migration.

## Client configuration

The LangChain client requires:

```text
AGENTIC_LAB_GATEWAY_BASE_URL
AGENTIC_LAB_GATEWAY_API_KEY
```

The gateway service itself owns the provider-side configuration declared in `config/litellm/config.yaml`, including environment references for:

```text
OPENAI_API_KEY
LITELLM_MASTER_KEY
```

`AGENTIC_LAB_GATEWAY_API_KEY` is deliberately named as a client credential instead of reading `LITELLM_MASTER_KEY` directly. A local environment may temporarily assign the master key value to it, but the client contract can later receive a scoped virtual key without changing application code.

`AGENTIC_LAB_MODEL` no longer selects the model for the LangChain/LangGraph path. During the incremental migration it remains relevant only to framework adapters that have not yet moved behind the gateway.

## Why the committed config looks like JSON

`config/litellm/config.yaml` uses JSON syntax intentionally. JSON is valid YAML syntax, so the proxy configuration remains YAML-compatible while the repository can validate the initial security invariants with Python's standard library only.

This keeps the foundation validation provider-free and avoids adding a YAML/runtime dependency solely for configuration validation.

## Reading recommendation

Read two short sections now:

1. LiteLLM Getting Started: **Proxy Server vs Python SDK**. Focus on why the proxy is a platform boundary rather than an application library.
2. LangChain `ChatOpenAI` API reference: **client parameters**, especially `base_url` and `api_key`.

You can ignore routing, virtual keys, budgets, observability callbacks, and provider-specific response extensions until their dedicated increments.
