# LlamaIndex gateway transport policy

## Purpose

This document defines the request-timeout and retry boundary for the LlamaIndex client that calls the governed LiteLLM gateway.

It is separate from the LlamaIndex Workflow orchestration timeout fixed by Issue #61 / PR #109.

## Version evidence

The project lockfile resolves:

```text
llama-index-llms-openai == 0.7.10
```

The corresponding upstream release is included in the `run-llama/llama_index` `v0.14.24` release. In that version, the OpenAI integration defaults are:

```text
timeout = 60.0 seconds
max_retries = 3
```

The same `max_retries` value controls the LlamaIndex retry decorator and is also passed to the underlying OpenAI client. Relying on those defaults would therefore make transport retry behavior implicit and could introduce multiple request attempts below the application evaluator/optimizer contract.

## Project policy

The LlamaIndex gateway adapter explicitly configures:

```text
request timeout = 30.0 seconds
client retries = 0
Workflow timeout = 45.0 seconds
```

The responsibilities are intentionally different:

```text
Application analysis retry
    semantic retry after deterministic validation
    owned by the shared evaluator/optimizer

LlamaIndex request timeout
    bound on one client -> gateway request
    30 seconds

LlamaIndex client retry
    disabled
    max_retries = 0

Workflow timeout
    orchestration wait bound
    45 seconds

LiteLLM/provider retry or fallback
    deployment/gateway responsibility
    must be configured explicitly if introduced
```

## Why client retries are disabled

The application already owns bounded semantic retries. A transport library retry is a different operation: it may repeat the same request before the deterministic evaluator has observed any result.

Keeping LlamaIndex client retries at zero avoids silently multiplying provider traffic and preserves the distinction between:

- `analysis_attempts`: application-owned reasoning/evaluation cycles;
- `model_calls`: framework/runtime model invocations observed by benchmark telemetry.

The project does not claim that a LlamaIndex callback can independently attest every upstream provider attempt performed inside the gateway. Provider/gateway retry telemetry is a deployment concern and must not be inferred from application callback counts alone.

## Timeout ordering

The request timeout is deliberately shorter than the Workflow timeout:

```text
30s request timeout < 45s orchestration timeout
```

This gives the client request an opportunity to fail before the outer orchestration deadline expires.

The two controls are not interchangeable. The Workflow timeout does not cancel a provider request by itself, and a request timeout does not define the maximum duration of the complete evaluator/optimizer workflow.

## Gateway ownership

The committed LiteLLM model mapping does not currently add an application-specific retry/fallback policy for the LlamaIndex path. This change does not introduce one.

If gateway retries or provider fallbacks are added later, they must be:

1. explicit in deployment configuration;
2. reviewed as a separate policy decision;
3. observable at the gateway/provider boundary;
4. evaluated for their effect on latency, cost, and provider-call accounting;
5. validated with new evidence rather than rewriting historical benchmark artifacts.

## Regression protection

Provider-free tests assert that the runtime constructs the LlamaIndex gateway client with:

```text
model = security-analysis
timeout = 30.0
max_retries = 0
```

No provider credential, external request, telemetry shortcut, or historical artifact is required to verify this contract.
