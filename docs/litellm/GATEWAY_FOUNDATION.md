# LiteLLM Gateway Foundation

## Documentation Freshness Check

Checked on 2026-09-03:

- LiteLLM official Getting Started;
- LiteLLM official Proxy / LLM Gateway guidance;
- current official LiteLLM container package releases.

Current pattern considered:

- LiteLLM supports both a Python SDK embedded in an application and a central Proxy Server;
- the Proxy exposes an OpenAI-compatible API and centralizes provider access;
- proxy capabilities include authentication, spend tracking, rate limiting, logging hooks, and model routing;
- current official container releases include the v1.98.0 line.

Decision for this lab:

- use the central Proxy / LLM Gateway architecture;
- keep provider selection out of domain/application contracts;
- expose the stable client-facing alias `security-analysis`;
- initially map that alias to the same upstream model used by the accepted framework benchmark;
- defer retries, fallbacks, budgets, virtual keys, database-backed spend policy, and observability until each policy has its own tests.

## Current boundary

```text
Framework adapter
      |
      | future OpenAI-compatible request
      v
security-analysis
      |
      v
LiteLLM Proxy
      |
      v
openai/gpt-5.6-luna
```

At this stage no framework adapter has been migrated yet. This increment only establishes the governed gateway configuration boundary.

## Why the committed config looks like JSON

`config/litellm/config.yaml` uses JSON syntax intentionally. JSON is valid YAML syntax, so the proxy configuration remains YAML-compatible while the repository can validate the initial security invariants with Python's standard library only.

This keeps the first increment provider-free and avoids adding a YAML/runtime dependency solely for configuration validation.

## Reading recommendation

Read the LiteLLM Getting Started comparison between **Proxy Server** and **Python SDK** now. Focus on the architectural difference and on the proxy's OpenAI-compatible boundary. Routing, virtual keys, and observability can wait until the corresponding project increments.
