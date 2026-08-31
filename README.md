# Agentic Security Framework Lab

[![quality](https://github.com/brunovicco/agentic-security-framework-lab/actions/workflows/quality.yml/badge.svg)](https://github.com/brunovicco/agentic-security-framework-lab/actions/workflows/quality.yml)

A framework-neutral lab for building, securing, evaluating, and comparing agentic AI systems using the same vulnerability-analysis workload.

The project is designed to answer a practical question:

> How do different agentic frameworks behave when they must solve the same security-sensitive problem under the same contracts, evidence, evaluation dataset, and runtime controls?

The current implementation uses **LangChain** for model abstraction and structured LLM output, and **LangGraph** for orchestration.

Planned framework implementations include CrewAI, LlamaIndex, and Agno.

## Core principle

```text
LLM reasons
software validates
policy constrains
runtime executes
evidence explains
```

The LLM is treated as a probabilistic reasoning component, not as the final authority.

Deterministic software remains responsible for validation, policy enforcement, fallback behavior, and security-sensitive decisions.

## Use case

The shared workload is vulnerability analysis:

```text
Analyze CVE-XXXX-YYYY and determine whether our environment is exposed.
```

The system receives vulnerability evidence and asset inventory data and produces a structured result containing:

- asset applicability
- severity
- recommendation
- confidence
- evidence provenance
- human-review requirement

## Architecture

The project keeps domain and application contracts independent from orchestration frameworks.

```text
                  Domain
                    │
                    ▼
               Application
                    │
                    ▼
            Ports / Contracts
                    │
        ┌───────────┴───────────┐
        │                       │
        ▼                       ▼
 Framework adapters       Shared evaluation
        │
        ├── LangChain
        ├── LangGraph
        ├── CrewAI       planned
        ├── LlamaIndex   planned
        └── Agno         planned
```

The current LangGraph workflow implements an evaluator-optimizer pattern:

```text
evidence
   │
   ▼
LLM analysis
   │
   ▼
deterministic evaluator
   │
   ├── accepted
   └── rejected
          │
          ▼
   evaluator feedback
          │
          ▼
     LLM retry
          │
          ▼
   deterministic evaluator
          │
          ├── accepted
          └── rejected
                 │
                 ▼
          oracle fallback
                 │
                 ▼
       deterministic policy
                 │
                 ▼
          AnalysisResult
```

The workflow allows a maximum of two LLM analysis attempts before falling back to deterministic assessment.

## Framework-neutral evidence

Agentic engines consume the same application-level evidence contract:

```text
AnalysisEvidenceBundle
├── vulnerability
├── assets
└── policy
```

Injected evidence is fail-closed on vulnerability identity: a bundle whose CVE identifier does not match the graph input is rejected before LLM analysis.

This boundary is intentionally reusable by future framework implementations.

## Evaluation dataset

The initial evaluation dataset contains five scenarios.

| Scenario | Purpose | Expected behavior |
| --- | --- | --- |
| `baseline-mixed` | affected and fixed assets | mixed applicability |
| `product-mismatch` | installed product differs from vulnerable product | `not_applicable` |
| `unknown-version` | version cannot be safely interpreted | `unknown` |
| `fixed-boundary` | exclusive affected-version boundary | `not_affected` |
| `adversarial-asset-id` | instruction-like text embedded in untrusted data | instruction remains data |

The adversarial scenario is deliberately narrow. It tests an instruction/data boundary and is **not** intended as proof of general prompt-injection resistance.

## Current LangGraph benchmark

The persisted benchmark was executed with:

```text
Framework: LangGraph
Pattern: evaluator-optimizer
Model: openai:gpt-5.6-luna
Scenarios: 5
Runs per scenario: 3
Total runs: 15
```

### Results

| Metric | Result |
| --- | ---: |
| Expected accuracy | 100.0% |
| First-attempt acceptance | 100.0% |
| Retry rate | 0.0% |
| Recovery rate | N/A |
| Fallback rate | 0.0% |
| Mean model calls | 1.00 |
| Mean latency | 2728.01 ms |
| p50 latency | 2643.41 ms |
| p95 latency | 3526.02 ms |
| Mean tokens/run | 613.80 |
| Total tokens | 9207 |

All 15 final results matched the framework-neutral expected truth.

The adversarial scenario also matched expected truth on all three runs without retry or deterministic fallback.

Recovery is reported as `N/A` because no run required the evaluator-optimizer retry path.

These measurements are intentionally small-sample engineering benchmarks. Latency percentiles should not be interpreted as production SLO measurements.

Full benchmark evidence:

- [`artifacts/benchmarks/langgraph/latest.md`](artifacts/benchmarks/langgraph/latest.md)
- [`artifacts/benchmarks/langgraph/latest.json`](artifacts/benchmarks/langgraph/latest.json)

## Security properties

The current implementation demonstrates several agentic-security controls:

- structured LLM output
- explicit application contracts
- deterministic applicability oracle
- deterministic policy enforcement
- conditional validation routing
- evaluator feedback
- bounded retry
- deterministic fallback
- fail-closed evidence identity validation
- separation of instructions from untrusted evidence
- external expected truth for evaluation
- runtime-path evidence
- token and latency measurement

A successful final result does not necessarily imply that the LLM succeeded.

For example:

```text
LLM attempt 1: wrong
LLM attempt 2: wrong
        │
        ▼
deterministic fallback
        │
        ▼
final system result: correct
```

This distinction between **model quality** and **system safety** is central to the project.

## Project structure

```text
src/agentic_lab/
├── domain/
├── application/
└── adapters/
    ├── fixtures/
    ├── langchain/
    └── langgraph/

tests/
└── unit/

scripts/
├── benchmark_langgraph.py
├── benchmark_langgraph_scenarios.py
├── run_llm_demo.py
└── quality_gate.py

artifacts/
└── benchmarks/
    └── langgraph/
        ├── latest.json
        └── latest.md

docs/
├── AGENTIC_FAST_TRACK.md
├── ARCHITECTURE.md
└── DEVELOPMENT.md
```

## Requirements

- Python 3.13
- [uv](https://docs.astral.sh/uv/)

Install the locked environment:

```bash
uv sync --frozen --all-groups
```

## Quality gate

Run the complete local engineering gate:

```bash
uv run python scripts/quality_gate.py
```

The gate covers:

- lockfile consistency
- Ruff linting
- Ruff formatting
- architecture boundaries
- Pyright strict typing
- pytest
- coverage threshold
- Bandit
- dependency vulnerability audit

The same quality gate runs in GitHub Actions.

## Run the deterministic/LLM demo

Configure a model:

```bash
export AGENTIC_LAB_MODEL="openai:<model-id>"
```

Load the API key without echoing it to the terminal:

```bash
read -s "OPENAI_API_KEY?OpenAI API key: "
echo
export OPENAI_API_KEY
```

Run:

```bash
uv run python scripts/run_llm_demo.py
```

## Run the single-scenario benchmark

```bash
uv run python scripts/benchmark_langgraph.py --runs 5
```

## Run the multi-scenario benchmark

```bash
uv run python scripts/benchmark_langgraph_scenarios.py --runs 3
```

The benchmark produces:

```text
artifacts/benchmarks/langgraph/latest.json
artifacts/benchmarks/langgraph/latest.md
```

## Documentation

- [Agentic fast track](docs/AGENTIC_FAST_TRACK.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Development](docs/DEVELOPMENT.md)
- [Engineering contract](AGENTS.md)

## Roadmap

### Current

- [x] deterministic vulnerability-analysis foundation
- [x] LangChain model abstraction
- [x] structured LLM analysis
- [x] LangGraph deterministic workflow
- [x] LangGraph evaluator-optimizer
- [x] deterministic validation and fallback
- [x] framework-neutral evaluation dataset
- [x] adversarial instruction/data-boundary scenario
- [x] latency and token benchmarks
- [x] persisted benchmark evidence

### Next

- [ ] CrewAI implementation
- [ ] cross-framework benchmark
- [ ] LlamaIndex implementation
- [ ] Agno implementation
- [ ] provider/model comparison
- [ ] richer adversarial evaluation dataset
- [ ] MCP integration and tool authorization
- [ ] observability and trace correlation
- [ ] human-in-the-loop workflows

## Why this project exists

Agentic frameworks make it easy to build impressive demos.

The harder engineering problem is building systems where probabilistic reasoning can be:

- constrained,
- validated,
- measured,
- audited,
- recovered,
- compared,
- and safely replaced.

This repository is a learning and engineering lab for exploring those tradeoffs under a consistent security-sensitive workload.
