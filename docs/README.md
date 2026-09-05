# Documentation map

This directory contains the design rationale, engineering contracts, evaluation methodology, security experiments, interoperability notes, and operational boundaries behind the Agentic Security Framework Lab.

The root [README](../README.md) is the portfolio landing page. Use this page when you want to go deeper without reading the documentation linearly.

## Choose a path by audience

### Developer / AI Engineer

Recommended order:

1. [Development guide](DEVELOPMENT.md)
2. [Architecture](ARCHITECTURE.md)
3. [Agentic fast track](AGENTIC_FAST_TRACK.md)
4. [Framework decision matrix](FRAMEWORK_DECISION_MATRIX.md)
5. [Final-evaluation methodology](evaluation/FINAL_EVALUATION.md)
6. [Engineering contract](../AGENTS.md)

Focus on:

- Domain → Application → Ports/Contracts → adapters;
- deterministic evaluation outside framework code;
- typed structured output;
- bounded retry and deterministic fallback;
- framework-specific orchestration differences;
- provider/gateway ownership;
- provider-free regression gates;
- evidence immutability.

### Engineering Manager / CIO / Platform Architect

Recommended order:

1. [Executive overview](EXECUTIVE_OVERVIEW.md)
2. [Architecture](ARCHITECTURE.md)
3. [Framework decision matrix](FRAMEWORK_DECISION_MATRIX.md)
4. [LiteLLM gateway foundation](litellm/GATEWAY_FOUNDATION.md)
5. [Privacy](PRIVACY.md)
6. [Current five-way evaluation](../artifacts/final-evaluation/phase15-20260905-v2/benchmarks/comparison/five-way-latest.md)

Focus on:

- which responsibilities remain stable when frameworks change;
- where policy and authority live;
- how provider access can be centralized;
- how model failures are contained;
- what the benchmark does and does not establish;
- what can be operated or governed independently of a specific agent framework.

### Recruiter / Interviewer

Recommended order:

1. [Root README](../README.md)
2. [Executive overview](EXECUTIVE_OVERVIEW.md)
3. [Framework decision matrix](FRAMEWORK_DECISION_MATRIX.md)
4. [Current evaluation report](../artifacts/final-evaluation/phase15-20260905-v2/benchmarks/comparison/five-way-latest.md)

What this path exposes quickly:

- multi-framework AI engineering rather than one-framework familiarity;
- security and governance reasoning;
- gateway/platform thinking;
- deterministic validation around probabilistic models;
- observability and privacy boundaries;
- reproducible evaluation and benchmark discipline;
- explicit architecture trade-offs.

### Security / Governance reviewer

Recommended order:

1. [Architecture](ARCHITECTURE.md)
2. [Privacy](PRIVACY.md)
3. [Security experiments](security/)
4. [MCP overview](MCP.md)
5. [MCP v2 local transport](mcp/V2_LOCAL_TRANSPORT.md)
6. [Architecture decision records](adr/)

Focus on:

- trust boundaries;
- instruction authority vs untrusted data;
- deterministic applicability controls;
- fallback behavior;
- tool/runtime boundaries;
- content-free logical telemetry;
- evidence provenance and immutability.

## Canonical documents

| Topic | Canonical document |
| --- | --- |
| Overall architecture and trust boundaries | [ARCHITECTURE.md](ARCHITECTURE.md) |
| Framework selection trade-offs | [FRAMEWORK_DECISION_MATRIX.md](FRAMEWORK_DECISION_MATRIX.md) |
| Developer onboarding | [DEVELOPMENT.md](DEVELOPMENT.md) |
| Executive / portfolio summary | [EXECUTIVE_OVERVIEW.md](EXECUTIVE_OVERVIEW.md) |
| Final evaluation methodology | [evaluation/FINAL_EVALUATION.md](evaluation/FINAL_EVALUATION.md) |
| Current accepted evaluation evidence | [Phase 15 five-way report](../artifacts/final-evaluation/phase15-20260905-v2/benchmarks/comparison/five-way-latest.md) |
| Provider boundary | [litellm/GATEWAY_FOUNDATION.md](litellm/GATEWAY_FOUNDATION.md) |
| MCP | [MCP.md](MCP.md) |
| Privacy / telemetry boundary | [PRIVACY.md](PRIVACY.md) |
| Architecture decisions | [adr/](adr/) |
| Security experiments | [security/](security/) |

## Design documents vs evidence artifacts

The repository intentionally separates two kinds of documentation.

### Design and methodology

Files under `docs/` explain:

- architecture;
- contracts;
- assumptions;
- methodology;
- security boundaries;
- architectural decisions;
- interpretation limits.

These documents may evolve with the code.

### Persisted evidence

Files under `artifacts/` record observed benchmark/evaluation results for a particular system state.

Accepted evidence is not rewritten to make later architecture look cleaner. Historical provider-native identifiers, latencies, token counts, retries, and fallbacks are preserved as generated.

That separation is deliberate: **documentation explains the system; evidence records what actually happened.**

## Language

The repository's primary technical documentation is English. A complete Portuguese landing page is available at [README.pt-br.md](../README.pt-br.md).
