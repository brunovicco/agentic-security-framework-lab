# Agentic Fast Track

## Purpose

The project compares multiple agentic frameworks using the same vulnerability-analysis workload.

The primary learning and portfolio focus is:

* LLM engineering
* LangChain
* LangGraph
* CrewAI
* LlamaIndex
* Agno
* tool use
* agent orchestration
* evaluation
* observability
* agentic security
* MCP

The deterministic domain foundation exists to provide trustworthy inputs, validation, and benchmark oracles. It is not the primary implementation focus.

## Core principle

```text
LLM reasons
software validates
policy constrains
runtime executes
evidence explains
```

## Framework boundary

Frameworks are adapters.

```text
Domain
   ↓
Application contracts
   ↓
Framework adapters
   ├── LangChain / LangGraph
   ├── CrewAI
   ├── LlamaIndex
   └── Agno
```

No framework owns the shared vulnerability-analysis domain or benchmark contract.

## Shared workload

Initial demo vulnerability:

```text
CVE-2026-9001

Product:
ExampleServer

Affected versions:
< 4.2

Severity:
critical

EPSS:
0.91

KEV:
listed
```

Environment:

```text
api-prod-01
ExampleServer 4.1
production
internet exposed

api-prod-02
ExampleServer 4.4
production
internal
```

Expected deterministic conclusion:

```text
api-prod-01 → affected
api-prod-02 → not affected

requires_human_review → true
```

## Comparison invariants

Every framework implementation must use the same:

* request contract
* result contract
* evidence
* fixture dataset
* deterministic policy
* evaluation cases
* expected outputs
* benchmark metrics

Framework-specific capabilities may be tested separately but must not silently change the shared benchmark.

## Framework roles

### LangChain

Use LangChain for:

* model integrations
* tool definitions
* tool calling
* structured model interfaces
* reusable LLM components

### LangGraph

Use LangGraph for:

* explicit state
* deterministic and LLM nodes
* conditional routing
* retries
* checkpointing
* persistence
* human-in-the-loop
* failure recovery

### CrewAI, LlamaIndex, and Agno

Implement the same workload through alternative framework adapters.

## Current implemented state

The original comparison roadmap is complete and the lab now also includes:

* a governed LiteLLM provider boundary plus persisted five-way provider-backed evaluation evidence;
* read-only and mutable MCP v2 STDIO experiments;
* application-owned exact source-aware mutable-action authorization;
* service-caller authentication separated from authorization;
* bounded, single-use, revocable and time-limited human approval;
* independent approver authorization;
* governed success and executor-failure evidence, including authenticated composition;
* fail-closed MCP protocol classification for uncertain post-executor failures;
* LangGraph, CrewAI Flow, LlamaIndex and Agno governed-action conformance against the direct application runtime;
* Agno mutable Step retry suppression and governed failure-provenance preservation;
* provider-free quality, security, MCP and OpenTelemetry CI gates.

The latest published milestone is v1.3.0; some failure-provenance and MCP hardening exists only on current `main` until a later release is explicitly published.

## Development sequence

```text
shared contracts
    ↓
deterministic fixtures and validation
    ↓
LangGraph / CrewAI / LlamaIndex / Agno implementations
    ↓
cross-framework evaluation and immutable evidence
    ↓
LiteLLM provider boundary
    ↓
MCP / OpenTelemetry / adversarial security
    ↓
governed mutable actions
    ↓
trusted caller identity and source-aware authorization
    ↓
human approval lifecycle and approver authorization
    ↓
executor-failure provenance and uncertain-execution hardening
    ↓
cross-framework governed failure conformance
```

## Current scope freeze

Do not expand domain modeling unless a concrete framework implementation or benchmark requires it.

Deferred work includes:

* generic evidence hierarchies
* generic version engines
* CPE matching
* full CVSS calculation
* production vulnerability ingestion
* AWS integration
* databases
* UI
* rich provenance infrastructure

These capabilities may be introduced later when they solve a demonstrated problem.
