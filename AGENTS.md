# Agentic Security Framework Lab — Engineering Contract

## Project

* Runtime: Python 3.13
* Profile: library
* Package: `agentic_lab`
* Layout: `src/agentic_lab`
* Dependency manager: uv
* Type checker: Pyright in strict mode
* Primary language for code, documentation, commits, and public artifacts: English

This repository is a learning and benchmarking lab for building the same vulnerability-analysis workload with multiple agentic frameworks while preserving shared domain contracts, deterministic behavior, evaluation scenarios, and evidence.

Keep public APIs small, typed, documented, and backward compatible.

Do not add a framework, runtime container, model provider, vector database, observability backend, or infrastructure dependency without a demonstrated requirement in the current phase.

Do not use `from __future__ import annotations`. Quote only the individual forward references that require deferred evaluation.

## Core engineering principles

The project follows this operating model:

```text
LLM reasons
software validates
policy constrains
runtime executes
evidence explains
```

Prefer deterministic software for validation, policy enforcement, authorization, calculations, and invariants.

Use LLMs for reasoning tasks where probabilistic behavior provides clear value.

Do not replace a deterministic rule with an LLM decision merely to make the workflow more agentic.

## Architecture ownership

Frameworks are adapters, not owners of the domain.

The intended dependency direction is:

```text
Domain
   ↓
Application
   ↓
Ports / Contracts
   ↓
Framework Adapters
```

Framework-specific code may depend on project contracts.

Project domain and application contracts must not depend on LangChain, LangGraph, LlamaIndex, CrewAI, Agno, LiteLLM, MCP SDKs, model-provider SDKs, or other orchestration frameworks.

Do not introduce framework-specific objects into shared domain contracts.

For example, domain models must not require objects such as LangGraph state classes, CrewAI tasks, LlamaIndex nodes, or Agno agent objects.

When architecture layers are introduced, preserve dependency direction and validate it through the project architecture gate.

## Comparative experiment integrity

The purpose of implementing multiple frameworks is comparison, not duplication.

Framework implementations must preserve, whenever applicable:

* domain concepts;
* input contracts;
* output contracts;
* tool contracts;
* datasets and fixtures;
* deterministic policies;
* evaluation scenarios;
* expected evidence;
* benchmark metrics.

Do not change the workload to make a framework appear stronger.

Framework-specific capabilities may be evaluated separately, but they must be identified explicitly as framework-specific experiments rather than silently changing the common benchmark.

## Deterministic-first development

Build and validate a deterministic vertical slice before introducing LLM or agent orchestration.

The deterministic implementation acts as a reference behavior for later agentic implementations.

Prefer this progression:

```text
contract
→ deterministic implementation
→ tests
→ evidence
→ framework adapter
→ evaluation
```

Do not introduce an LLM when the current problem can be solved reliably with ordinary software.

## Evidence and provenance

Evidence is a first-class project concern.

Keep observed facts, derived assessments, policy decisions, and execution actions conceptually distinct.

Do not represent inferred or generated information as observed evidence.

Preserve provenance when information originates from external vulnerability sources, tools, retrieval systems, or other repositories.

Where practical, make evidence reproducible and suitable for later comparison across framework implementations.

## Security and side effects

Treat external inputs, retrieved content, model output, tool output, and MCP responses as untrusted until validated.

Never read, write, log, commit, or transmit secrets.

Use MCP only for structured external access and validate its configuration through the project quality gate.

Keep mutations and external side effects explicitly permission-gated.

Prefer read-only tools while learning the orchestration model.

Do not introduce actions such as remediation-ticket creation, infrastructure mutation, or automated approval until authorization, validation, failure handling, audit evidence, and human-review behavior are explicitly designed.

Fail closed when an authorization or policy decision cannot be established safely.

## Framework and dependency freshness

Agentic frameworks evolve quickly.

Before implementing or materially changing behavior that depends on LangChain, LangGraph, LlamaIndex, CrewAI, Agno, LiteLLM, MCP, model-provider SDKs, or similar fast-moving dependencies:

1. Consult current official documentation.
2. Verify the installed or intended version.
3. Identify the current recommended pattern.
4. Check for relevant deprecations or migration guidance.
5. Record implementation impact when the findings materially affect the design.

Prefer official documentation and primary sources over tutorials when determining current APIs or architectural patterns.

Do not copy obsolete framework examples merely because they are common in older tutorials.

## Incremental working method

Implement one coherent concept at a time.

Prefer:

```text
one concept
+ one small increment
+ focused tests
+ validation
```

over large batches of unrelated changes.

For each meaningful change:

1. Confirm the problem and acceptance criteria.
2. Inspect affected contracts, implementation, tests, and documentation.
3. Introduce the smallest coherent change.
4. Add or update behavior-focused tests when behavior changes.
5. Run the relevant focused checks.
6. Run the complete quality gate before completion.
7. Review the diff for accidental scope expansion.
8. Report verification evidence, assumptions, compatibility impact, and remaining risks.

Do not combine unrelated refactors with feature work.

Do not introduce abstractions solely because they may be useful later.

Prefer the simplest design that preserves the intended architectural boundary.

## Quality gate

The project-owned quality gate is:

```bash
uv run python scripts/quality_gate.py
```

Use:

```bash
uv run python scripts/quality_gate.py --list
```

to discover named checks and:

```bash
uv run python scripts/quality_gate.py --check NAME
```

for focused validation.

Run the complete gate before considering a change complete.

The expected baseline includes:

* dependency lock validation;
* Ruff linting;
* Ruff formatting;
* architecture validation;
* MCP configuration validation;
* governance validation when enabled;
* loop-schema validation;
* Pyright strict type checking;
* Pytest;
* coverage requirements;
* Bandit;
* dependency vulnerability auditing.

Distinguish regressions introduced by the current change from pre-existing failures.

## Governance

Repository-development governance and the product's AI-security domain are separate concerns.

Do not enable a harness governance profile merely because this project studies agentic security.

Enable governance controls only when they solve a concrete repository or delivery requirement.

When governance is enabled:

* run `uv run python scripts/governance_gate.py`;
* keep records under `governance/` current;
* treat framework mappings as support statements rather than certification claims;
* keep generated governance evidence metadata-only.

## Decision records

Use an ADR when a decision is:

* architecturally significant;
* difficult or costly to reverse;
* likely to be questioned later;
* relevant across multiple phases or framework implementations.

Do not create ADRs for routine implementation details.

Important project-wide architectural decisions should explain the context, alternatives, decision, consequences, and conditions that would justify revisiting the decision.
