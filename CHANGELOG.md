# Changelog

## 1.0.0 - 2026-09-05

First portfolio-complete release of the Agentic Security Framework Lab.

### Added

- Framework-neutral Domain/Application contracts with framework adapters for LangGraph, CrewAI Agent/Crew, CrewAI Flow, LlamaIndex Workflow, and Agno Workflow.
- Deterministic validation, bounded semantic retries, oracle fallback, and human-review policy.
- Canonical five-framework evaluation and immutable Phase 15 final-evaluation evidence.
- Centralized LiteLLM gateway boundary using governed alias `security-analysis`.
- MCP 2026-07-28 / Python SDK v2 STDIO integration and real subprocess smoke coverage.
- Framework-neutral, content-free logical analysis observability with OpenTelemetry compatibility checks.
- Bilingual English/Portuguese portfolio landing pages, audience-based documentation navigation, executive overview, and expanded developer onboarding.

### Hardened

- CrewAI proprietary tracing disabled for final evaluation without disabling project-owned OpenTelemetry.
- LlamaIndex Workflow synchronous analysis offloaded from the event loop so the orchestration timeout remains responsive.
- LlamaIndex gateway request policy made explicit: 30-second request timeout, zero client-local retries, separate 45-second Workflow orchestration bound.

### Evidence

- Accepted final evaluation bundle: `artifacts/final-evaluation/phase15-20260905-v2/`.
- 75 framework executions produced 76 actual model calls and 100% expected final outcomes.
- Historical evaluation artifacts remain immutable; runtime-hardening commits after the accepted Phase 15 evidence do not rewrite that evidence.
