# Agentic Security Framework Lab

[![quality](https://github.com/brunovicco/agentic-security-framework-lab/actions/workflows/quality.yml/badge.svg)](https://github.com/brunovicco/agentic-security-framework-lab/actions/workflows/quality.yml)

A controlled engineering lab for comparing **LangGraph, CrewAI, LlamaIndex, and Agno** on the same security-sensitive agentic workload.

The project asks a narrow but practical question:

> What changes when different agentic orchestration abstractions solve the same problem under the same evidence, expected truth, deterministic validation, retry, fallback, policy, and model?

The workload is vulnerability applicability analysis. The LLM may reason about evidence, but it never owns the security-sensitive source of truth.

## Core invariant

```text
LLM reasons
software validates
policy constrains
runtime executes
evidence explains
```

The LLM is a probabilistic reasoning component, not the final authority.

Application-owned deterministic software remains responsible for:

- evidence identity validation;
- applicability validation;
- bounded retry decisions;
- deterministic oracle fallback;
- human-review policy;
- final `AnalysisResult` construction.

## Five-way benchmark

The current official benchmark compares five orchestration variants using the same model and the same five scenarios.

```text
Model: openai:gpt-5.6-luna
Scenarios: 5
Repetitions per scenario: 3
Runs per variant: 15
Sampling: provider default
```

| Variant | Expected accuracy | First pass | Mean calls | Mean latency | p50 latency | Mean tokens |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| LangGraph evaluator-optimizer | 100% | 100% | 1.00 | **2728.01 ms** | **2643.41 ms** | **613.80** |
| CrewAI Agent + Task + Crew | 100% | 100% | 1.00 | 2866.79 ms | 2818.60 ms | 1143.33 |
| CrewAI Flow + direct structured LLM | 100% | 100% | 1.00 | 2847.78 ms | 2739.98 ms | 630.27 |
| LlamaIndex Workflow + `structured_predict()` | 100% | 100% | 1.00 | 2963.03 ms | 2837.52 ms | 630.13 |
| Agno Workflow + native `Loop` / `Condition` | 100% | 100% | 1.00 | 3268.84 ms | 3159.27 ms | 634.20 |

### What the benchmark suggests

For this controlled workload, the three lighter orchestration variants added after the LangGraph baseline converged to a very similar token envelope:

```text
LlamaIndex Workflow   630.13 tokens/run
CrewAI Flow           630.27 tokens/run
Agno Workflow         634.20 tokens/run
```

Their spread is only **0.65%**.

By contrast, the CrewAI `Agent + Task + Crew` envelope used **1143.33 tokens/run**. Switching from that abstraction to CrewAI Flow removed **96.89%** of the Agent/Crew token excess above the LangGraph baseline; LlamaIndex removed **96.92%**, and Agno removed **96.15%**.

The useful conclusion is not that one framework is universally better:

> **For this workload, orchestration abstraction choice affected token cost more than the difference among the lighter framework implementations.**

Latency tells a different story. Agno remained in the same light token cluster but showed higher mean and p50 latency in this fifteen-run sample. Those latency results are descriptive only.

Full evidence:

- [Five-way human-readable report](artifacts/benchmarks/comparison/five-way-latest.md)
- [Five-way machine-readable artifact](artifacts/benchmarks/comparison/five-way-latest.json)
- [Framework decision matrix](docs/FRAMEWORK_DECISION_MATRIX.md)

### What the benchmark does **not** prove

- It does not establish statistical significance.
- It does not establish production SLOs.
- At `n=15`, nearest-rank p95 is the sample maximum and should be treated only as a small-sample tail indicator.
- It does not establish a general framework ranking.
- The adversarial asset-ID scenario is a narrow instruction/data-boundary test, not proof of broad prompt-injection resistance.
- All five official samples happened to reach 100% first-pass acceptance, so the official run does not create a quality ranking between frameworks.

## LangGraph adversarial evidence-plane baseline

The first official adversarial v2 baseline moves attacker-controlled instructions from structured asset identifiers into explicit vendor, retrieved, and internal evidence documents. Provenance describes each source, while document content remains untrusted and has zero instruction authority.

```text
Model: openai:gpt-5.6-luna
Scenarios: 6
Repetitions per scenario: 3
Runs: 18
Sampling: provider default
```

| Task accuracy | Security pass | Model attack success | Unsafe acceptance | Retry | Fallback | Mean latency | Mean tokens |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 100% | 100% | 0% | 0% | 0% | 0% | 2503.86 ms | 763.17 |

Across these 18 observed runs, all task and security assertions passed and none of the six deterministic attacker goals succeeded at the model level. Consequently, rejection, recovery, and control-containment rates remain `N/A`: this sample did not exercise live containment after a successful model attack.

The v2 mean of 763.17 tokens/run is 22.9% above the adversarial v1 mean of 620.80. This is a descriptive input-cost difference for the added documents and provenance, not a framework or model performance claim.

This narrow synthetic result does not establish general prompt-injection resistance. See the [human-readable report](artifacts/adversarial-v2/langgraph/latest.md), [machine-readable artifact](artifacts/adversarial-v2/langgraph/latest.json), and [evidence-plane design and interpretation](docs/security/ADVERSARIAL_V2_EVIDENCE_PLANE.md).

## Shared workload

Each implementation analyzes the same framework-neutral evidence contract:

```text
AnalysisEvidenceBundle
├── vulnerability
├── assets
├── policy
└── documents (optional)
```

A request such as:

```text
Analyze CVE-XXXX-YYYY and determine whether our environment is exposed.
```

produces a structured result containing:

- asset applicability;
- severity;
- recommendation;
- confidence;
- evidence provenance;
- human-review requirement.

The LLM does not own the CVE identifier, evidence provenance, deterministic policy, or final authority.

## Shared evaluator-optimizer control loop

Every benchmark variant is constrained by the same application-owned control semantics:

```text
evidence
   │
   ▼
probabilistic analysis
   │
   ▼
deterministic evaluator
   │
   ├── accepted ─────────────────────────────┐
   │                                         │
   └── rejected                              │
          │                                  │
          ▼                                  │
   evaluator feedback                        │
          │                                  │
          ▼                                  │
     bounded retry                           │
          │                                  │
          ▼                                  │
   deterministic evaluator                   │
          │                                  │
          ├── accepted ──────────────────────┤
          │                                  │
          └── exhausted                      │
                 │                           │
                 ▼                           │
        deterministic oracle                 │
                 │                           │
                 └──────────────┬────────────┘
                                ▼
                      deterministic policy
                                │
                                ▼
                         AnalysisResult
```

A correct final system result therefore does not necessarily mean that the LLM was correct. The runtime can reject unsafe reasoning and recover through bounded retry or deterministic fallback.

That distinction between **model quality** and **system safety** is central to the lab.

## Framework implementations

| Framework / abstraction | Native orchestration used | Structured reasoning path | Application-owned deterministic controls |
| --- | --- | --- | --- |
| LangGraph | graph nodes + conditional routing | LangChain structured model output | yes |
| CrewAI Agent/Crew | `Agent` + `Task` + `Crew` | structured CrewAI output | yes, external evaluator |
| CrewAI Flow | Flow routing/state | direct structured `LLM.call()` | yes |
| LlamaIndex Workflow | typed Workflow events | `structured_predict()` | yes |
| Agno Workflow | `Workflow` + `Loop` + `Condition` | Agent structured output | yes |

The repository intentionally keeps framework adapters below the application boundary so orchestration can change without moving security authority into a framework.

See [Architecture](docs/ARCHITECTURE.md) for the detailed design and trust boundaries.

## Evaluation dataset

| Scenario | Purpose | Expected behavior |
| --- | --- | --- |
| `baseline-mixed` | affected and fixed assets | mixed applicability |
| `product-mismatch` | installed product differs from vulnerable product | `not_applicable` |
| `unknown-version` | version cannot be safely interpreted | `unknown` |
| `fixed-boundary` | exclusive affected-version boundary | `not_affected` |
| `adversarial-asset-id` | instruction-like text embedded in untrusted data | instruction remains data |

The expected truth is external to every framework implementation.

## Security properties demonstrated

The current implementation exercises:

- structured LLM output;
- explicit application contracts;
- domain/application isolation from framework adapters;
- fail-closed CVE/evidence identity validation;
- deterministic applicability evaluation;
- evaluator feedback;
- bounded retry;
- deterministic fallback;
- deterministic human-review policy;
- separation of instructions from untrusted evidence;
- framework-level hidden retry suppression where relevant;
- framework telemetry suppression where relevant;
- per-run model-call accounting;
- token accounting;
- latency measurement;
- external expected truth;
- persisted benchmark evidence.

The security model is documented in [Architecture](docs/ARCHITECTURE.md).

## Project structure

```text
src/agentic_lab/
├── domain/
├── application/
└── adapters/
    ├── agno/
    ├── crewai/
    ├── fixtures/
    ├── langchain/
    ├── langgraph/
    └── llamaindex/

scripts/
├── benchmark_langgraph_scenarios.py
├── benchmark_crewai_scenarios.py
├── benchmark_crewai_flow_scenarios.py
├── benchmark_llamaindex_workflow_scenarios.py
├── benchmark_agno_workflow_scenarios.py
├── compare_five_way_benchmarks.py
└── quality_gate.py

artifacts/benchmarks/
├── langgraph/
├── crewai/
├── crewai-flow/
├── llamaindex-workflow/
├── agno-workflow/
└── comparison/
```

## Reproduce the environment

Requirements:

- Python 3.13
- [uv](https://docs.astral.sh/uv/)

Install the locked environment:

```bash
uv sync --frozen --all-groups
```

Run the complete engineering gate:

```bash
uv run python scripts/quality_gate.py
```

The gate covers lockfile consistency, Ruff, architecture checks, governance checks, Pyright strict typing, pytest, coverage, Bandit, and dependency auditing. The same gate runs in GitHub Actions.

## Run a real-provider benchmark

Set the model without embedding credentials in repository files:

```bash
export AGENTIC_LAB_MODEL="openai:gpt-5.6-luna"
```

Load the API key without echoing it:

```bash
read -s "OPENAI_API_KEY?OpenAI API key: "
echo
export OPENAI_API_KEY
```

Examples:

```bash
uv run python scripts/benchmark_langgraph_scenarios.py --runs 3
uv run python scripts/benchmark_langgraph_adversarial_v2.py --runs 3
uv run python scripts/benchmark_crewai_scenarios.py --runs 3
uv run python scripts/benchmark_crewai_flow_scenarios.py --runs 3
uv run python scripts/benchmark_llamaindex_workflow_scenarios.py --runs 3
AGNO_TELEMETRY=false uv run python scripts/benchmark_agno_workflow_scenarios.py --runs 3
```

Regenerate the current consolidated comparison:

```bash
uv run python scripts/compare_five_way_benchmarks.py
```

## Documentation

- [Architecture and security model](docs/ARCHITECTURE.md)
- [Framework decision matrix](docs/FRAMEWORK_DECISION_MATRIX.md)
- [Five-way benchmark report](artifacts/benchmarks/comparison/five-way-latest.md)
- [LangGraph adversarial v2 report](artifacts/adversarial-v2/langgraph/latest.md)
- [Adversarial v2 evidence-plane design](docs/security/ADVERSARIAL_V2_EVIDENCE_PLANE.md)
- [Agentic fast track](docs/AGENTIC_FAST_TRACK.md)
- [Development](docs/DEVELOPMENT.md)
- [MCP](docs/MCP.md)
- [Privacy](docs/PRIVACY.md)
- [Engineering contract](AGENTS.md)
- [Portuguese README](README.pt-br.md)

## Current status and next experiments

Completed:

- [x] framework-neutral vulnerability-analysis domain and evidence contract;
- [x] deterministic evaluator, policy, retry, and oracle fallback;
- [x] LangGraph evaluator-optimizer;
- [x] CrewAI Agent/Task/Crew implementation;
- [x] CrewAI Flow direct-LLM implementation;
- [x] LlamaIndex Workflow implementation;
- [x] Agno Workflow implementation;
- [x] shared five-scenario evaluation dataset;
- [x] official 15-run benchmark for every variant;
- [x] persisted five-way comparison;
- [x] explicit evidence-document provenance and instruction-authority boundary;
- [x] official 18-run LangGraph adversarial v2 evidence-plane baseline;
- [x] strict local/CI quality gate.

Candidate next experiments:

- [ ] isolated benchmark-sensitivity control that can exercise model-attack and containment paths;
- [ ] reuse the adversarial v2 suite across the lighter framework variants;
- [ ] model/provider comparison under the same framework-neutral controls;
- [ ] MCP/tool authorization and least-privilege experiments;
- [ ] trace correlation and observability comparison;
- [ ] controlled human-in-the-loop workflows;
- [ ] larger samples for latency distributions and uncertainty estimates.

## Why this project exists

Agentic frameworks make impressive demos easy to build. The harder problem is designing systems where probabilistic reasoning can be constrained, validated, measured, audited, recovered, compared, and safely replaced.

This repository treats framework choice as an implementation detail beneath a stable security boundary and uses reproducible evidence to study the tradeoffs.
