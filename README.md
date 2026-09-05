# Agentic Security Framework Lab

[![quality](https://github.com/brunovicco/agentic-security-framework-lab/actions/workflows/quality.yml/badge.svg)](https://github.com/brunovicco/agentic-security-framework-lab/actions/workflows/quality.yml)

A controlled engineering lab for comparing **LangGraph, CrewAI, LlamaIndex, and Agno** on the same security-sensitive agentic workload.

The project asks a narrow but practical question:

> What changes when different agentic orchestration abstractions solve the same problem under the same evidence, expected truth, deterministic validation, retry, fallback, policy, and governed model boundary?

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

## Current five-way final evaluation

The current-state evaluation runs all five orchestration variants through the same centralized LiteLLM gateway boundary.

```text
Governed client alias: security-analysis
Scenarios: 5
Repetitions per scenario: 3
Runs per variant: 15
Framework executions: 75
Model calls: 76
Sampling: provider default
Evaluated commit: dd48c2490fc4ec1c76093577f7944d76a6fbc572
```

The alias `security-analysis` is the governed identity requested by every framework client. It is deliberately different from a provider-native model identifier: provider/model mapping belongs behind the LiteLLM gateway.

| Variant | Expected accuracy | First pass | Mean calls | Mean latency | p50 latency | Mean tokens |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| LangGraph evaluator-optimizer | 100% | 100% | 1.00 | 3404.92 ms | 3447.83 ms | **611.33** |
| CrewAI Agent + Task + Crew | 100% | 100% | 1.00 | 2987.15 ms | 3049.42 ms | 1136.60 |
| CrewAI Flow + direct structured LLM | 100% | 100% | 1.00 | 3172.98 ms | 3082.20 ms | 630.60 |
| LlamaIndex Workflow + `structured_predict()` | 100% | **93.33%** | **1.07** | 3214.98 ms | **2727.60 ms** | 732.20 |
| Agno Workflow + native `Loop` / `Condition` | 100% | 100% | 1.00 | **2980.14 ms** | 3015.20 ms | 632.00 |

### What the final evaluation shows

All five variants reached **100% expected final accuracy** under the same application-owned controls.

One LlamaIndex `product-mismatch` execution is intentionally different from the others:

```text
LLM attempt 1
    ↓ rejected by deterministic validation
LLM attempt 2
    ↓ rejected by deterministic validation
oracle fallback
    ↓
expected final result
```

That run produced two model calls, which is why the complete evaluation has **75 framework executions but 76 model calls**. The anomaly is preserved rather than normalized because the lab is designed to expose whether success came from first-pass model reasoning, bounded recovery, or deterministic fallback.

The current token shape is also informative:

```text
LangGraph                611.33 tokens/run
CrewAI Flow              630.60 tokens/run
Agno Workflow            632.00 tokens/run
LlamaIndex Workflow      732.20 tokens/run
CrewAI Agent/Crew       1136.60 tokens/run
```

CrewAI Flow and Agno were almost identical in this sample, while the higher LlamaIndex average includes the one execution that made an extra model call. The CrewAI comparison remains especially useful because two abstractions inside the **same framework** produced very different token envelopes.

The useful conclusion is not that one framework is universally better:

> **For this workload, orchestration abstraction can materially affect execution cost even when security authority, expected truth, gateway boundary, and model-facing alias remain shared.**

Latency tells a different story. Agno had the lowest mean, LlamaIndex the lowest p50, and LangGraph the highest mean in this particular fifteen-run sample. Those differences are descriptive only and do not establish a universal performance ranking.

Current immutable evidence:

- [Phase 15 five-way report](artifacts/final-evaluation/phase15-20260905-v2/benchmarks/comparison/five-way-latest.md)
- [Phase 15 machine-readable comparison](artifacts/final-evaluation/phase15-20260905-v2/benchmarks/comparison/five-way-latest.json)
- [Phase 15 manifest](artifacts/final-evaluation/phase15-20260905-v2/manifest.json)
- [Final-evaluation methodology](docs/evaluation/FINAL_EVALUATION.md)
- [Framework decision matrix](docs/FRAMEWORK_DECISION_MATRIX.md)

### What the final evaluation does **not** prove

- It does not establish statistical significance.
- It does not establish production SLOs.
- At `n=15`, nearest-rank p95 is the sample maximum and should be treated only as a small-sample tail indicator.
- It does not establish a general framework ranking.
- The adversarial asset-ID scenario is a narrow instruction/data-boundary test, not proof of broad prompt-injection resistance.
- The single observed LlamaIndex fallback does not establish a stable framework-level retry or token-cost characteristic.
- The `security-analysis` alias is not independent attestation of the provider-native model selected behind the gateway.

## Historical benchmark evidence

The repository preserves earlier provider-direct benchmark artifacts as immutable historical evidence. They document the system at the time they were generated and are not rewritten to match the current gateway-backed architecture.

Historical five-way evidence:

- [Historical five-way report](artifacts/benchmarks/comparison/five-way-latest.md)
- [Historical five-way machine-readable artifact](artifacts/benchmarks/comparison/five-way-latest.json)

Historical provider-native model identifiers in those artifacts remain intentionally unchanged.

## LangGraph adversarial evidence-plane baseline

The first official adversarial v2 baseline moves attacker-controlled instructions from structured asset identifiers into explicit vendor, retrieved, and internal evidence documents. Provenance describes each source, while document content remains untrusted and has zero instruction authority.

This is historical provider-backed evidence and retains the provider-native model identity recorded when it was generated.

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

A separate noncanonical positive control deliberately granted document content instruction authority. The model followed the forced-status attack on both attempts; deterministic validation rejected both drafts and the oracle fallback produced a task-correct, security-valid final result. This calibrates the attack and containment telemetry without changing the canonical prompt. See the [sensitivity-control report](artifacts/adversarial-v2-sensitivity/langgraph/latest.md) and [machine-readable trace](artifacts/adversarial-v2-sensitivity/langgraph/latest.json).

## Lightweight-workflow adversarial v2 smoke

CrewAI Flow, LlamaIndex Workflow, and Agno Workflow each executed the same six evidence-plane scenarios once with `openai:gpt-5.6-luna`. All 18 attempt traces were manually reviewed after generation.

These are also historical compatibility-smoke artifacts and intentionally keep their original provider-native identity.

| Workflow | Runs | Task accuracy | Security pass | Model attack success | Unsafe acceptance | Retry | Fallback | Mean latency | Mean tokens |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| CrewAI Flow | 6 | 100% | 100% | 0% | 0% | 0% | 0% | 3947.03 ms | 799.17 |
| LlamaIndex Workflow | 6 | 100% | 100% | 0% | 0% | 0% | 0% | 2843.26 ms | 793.17 |
| Agno Workflow | 6 | 100% | 100% | 0% | 0% | 0% | 0% | 3110.31 ms | 795.00 |

Every draft matched the deterministic applicability oracle on its first attempt, and none matched its scenario-specific attacker goal. These one-repetition artifacts confirm provider-backed contract compatibility; they are non-baseline smoke evidence and do not support framework or performance rankings. See the [manual review record](docs/security/ADVERSARIAL_V2_WORKFLOW_SMOKE_REVIEW.md).

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

| Framework / abstraction | Native orchestration used | Structured reasoning path | Provider boundary | Application-owned deterministic controls |
| --- | --- | --- | --- | --- |
| LangGraph | graph nodes + conditional routing | LangChain structured model output | LiteLLM `security-analysis` | yes |
| CrewAI Agent/Crew | `Agent` + `Task` + `Crew` | structured CrewAI output | LiteLLM `security-analysis` | yes, external evaluator |
| CrewAI Flow | Flow routing/state | direct structured `LLM.call()` | LiteLLM `security-analysis` | yes |
| LlamaIndex Workflow | typed Workflow events | `structured_predict()` | LiteLLM `security-analysis` | yes |
| Agno Workflow | `Workflow` + `Loop` + `Condition` | Agent structured output | LiteLLM `security-analysis` | yes |

The repository intentionally keeps framework adapters below the application boundary so orchestration can change without moving security authority into a framework.

All five provider-backed paths now cross the centralized LiteLLM gateway. Provider credentials and provider-native model identifiers remain outside framework adapters; each client knows the stable `security-analysis` alias, gateway endpoint, and client credential required by its framework integration.

See [Architecture](docs/ARCHITECTURE.md) for the detailed design and trust boundaries and [LiteLLM gateway foundation](docs/litellm/GATEWAY_FOUNDATION.md) for the provider-access boundary.

## Evaluation dataset

| Scenario | Purpose | Expected behavior |
| --- | --- | --- |
| `baseline-mixed` | affected and fixed assets | mixed applicability |
| `product-mismatch` | installed product differs from vulnerable product | `not_applicable` |
| `unknown-version` | version cannot be safely interpreted | `unknown` |
| `fixed-boundary` | exclusive affected-version boundary | `not_affected` |
| `adversarial-asset-id` | instruction-like text embedded in untrusted data | instruction remains data |

The expected truth is external to every framework implementation and to the configured upstream model.

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
- framework proprietary telemetry suppression where relevant;
- per-run model-call accounting;
- token accounting;
- latency measurement;
- external expected truth;
- persisted immutable evaluation evidence;
- a governed LiteLLM alias shared by every framework client;
- separation between application-owned logical OpenTelemetry and provider/framework telemetry.

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
    ├── gateway.py
    ├── langchain/
    ├── langgraph/
    └── llamaindex/

config/
└── litellm/
    └── config.yaml

scripts/
├── benchmark_langgraph_scenarios.py
├── benchmark_crewai_scenarios.py
├── benchmark_crewai_flow_scenarios.py
├── benchmark_llamaindex_workflow_scenarios.py
├── benchmark_agno_workflow_scenarios.py
├── compare_five_way_benchmarks.py
├── run_final_evaluation.py
└── quality_gate.py

artifacts/
├── benchmarks/              # historical benchmark evidence
└── final-evaluation/
    └── phase15-20260905-v2/ # current immutable five-way evidence
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

The gate covers lockfile consistency, Ruff, architecture checks, governance checks, Pyright strict typing, pytest, coverage, Bandit, and dependency auditing. The same provider-free gate runs in GitHub Actions.

## Run provider-backed experiments through the gateway

All current framework clients use the centralized LiteLLM boundary. `AGENTIC_LAB_MODEL` is obsolete for provider selection.

Load the provider key and a local gateway master key without committing either secret:

```bash
read -s "OPENAI_API_KEY?OpenAI API key: "
echo
export OPENAI_API_KEY

read -s "LITELLM_MASTER_KEY?LiteLLM master key: "
echo
export LITELLM_MASTER_KEY
```

Install the pinned proxy as a `uv` tool, outside the project dependency graph, and start it with the committed configuration:

```bash
uv tool install 'litellm[proxy]==1.98.0'
litellm --config config/litellm/config.yaml
```

In another shell, configure the client-facing gateway contract. A local setup may temporarily use the master key value as the client credential; a deployment may replace it with a scoped credential without changing application code.

```bash
export AGENTIC_LAB_GATEWAY_BASE_URL="http://localhost:4000"
export AGENTIC_LAB_GATEWAY_API_KEY="$LITELLM_MASTER_KEY"
```

For direct framework benchmark runs that should preserve the privacy boundary used by the accepted Phase 15 evaluation, apply the same vendor-specific telemetry guards. `CREWAI_TESTING=true` is required here to suppress the pinned CrewAI 1.15.18 first-execution trace-collection path; project-owned OpenTelemetry remains enabled because `OTEL_SDK_DISABLED` is deliberately not used.

```bash
export CREWAI_TRACING_ENABLED=false
export CREWAI_DISABLE_TELEMETRY=true
export CREWAI_DISABLE_TRACKING=true
export CREWAI_TESTING=true
export AGNO_TELEMETRY=false
```

Then run an individual framework benchmark when exploring one adapter:

```bash
uv run python scripts/benchmark_langgraph_scenarios.py --runs 3
uv run python scripts/benchmark_crewai_scenarios.py --runs 3
uv run python scripts/benchmark_crewai_flow_scenarios.py --runs 3
uv run python scripts/benchmark_llamaindex_workflow_scenarios.py --runs 3
uv run python scripts/benchmark_agno_workflow_scenarios.py --runs 3
```

For a new controlled five-way provider-backed evidence run, prefer the final-evaluation runner. It executes benchmarks in an isolated temporary workspace, validates the shared alias/repetition contract, applies the vendor telemetry guards required by the accepted methodology, and persists a new append-only bundle:

```bash
uv run python scripts/run_final_evaluation.py
```

Do not reuse `phase15-20260905-v2`; that run id belongs to the accepted immutable Phase 15 evidence. Provider-backed final evaluation is intentionally not part of normal CI.

## Documentation

- [Architecture and security model](docs/ARCHITECTURE.md)
- [Framework decision matrix](docs/FRAMEWORK_DECISION_MATRIX.md)
- [Final-evaluation methodology](docs/evaluation/FINAL_EVALUATION.md)
- [LiteLLM gateway foundation](docs/litellm/GATEWAY_FOUNDATION.md)
- [LiteLLM gateway ADR](docs/adr/0002-centralize-llm-provider-access-behind-litellm-proxy.md)
- [Current Phase 15 five-way report](artifacts/final-evaluation/phase15-20260905-v2/benchmarks/comparison/five-way-latest.md)
- [Historical five-way benchmark report](artifacts/benchmarks/comparison/five-way-latest.md)
- [LangGraph adversarial v2 report](artifacts/adversarial-v2/langgraph/latest.md)
- [Adversarial v2 evidence-plane design](docs/security/ADVERSARIAL_V2_EVIDENCE_PLANE.md)
- [Adversarial v2 sensitivity-control methodology](docs/security/ADVERSARIAL_V2_SENSITIVITY_CONTROL.md)
- [LangGraph adversarial v2 sensitivity-control result](artifacts/adversarial-v2-sensitivity/langgraph/latest.md)
- [Adversarial v2 lightweight-workflow smoke review](docs/security/ADVERSARIAL_V2_WORKFLOW_SMOKE_REVIEW.md)
- [Agentic fast track](docs/AGENTIC_FAST_TRACK.md)
- [Development](docs/DEVELOPMENT.md)
- [MCP](docs/MCP.md)
- [Privacy](docs/PRIVACY.md)
- [Engineering contract](AGENTS.md)
- [Portuguese README](README.pt-br.md)

## Current status and candidate next experiments

Completed:

- [x] framework-neutral vulnerability-analysis domain and evidence contract;
- [x] deterministic evaluator, policy, bounded retry, and oracle fallback;
- [x] LangGraph evaluator-optimizer;
- [x] CrewAI Agent/Task/Crew implementation;
- [x] CrewAI Flow direct-LLM implementation;
- [x] LlamaIndex Workflow implementation;
- [x] Agno Workflow implementation;
- [x] shared five-scenario evaluation dataset and historical five-way baseline;
- [x] adversarial v2 evidence-plane baseline, sensitivity control, and lightweight-workflow smoke evidence;
- [x] centralized LiteLLM gateway with governed `security-analysis` alias;
- [x] LangGraph, CrewAI Agent/Crew, CrewAI Flow, LlamaIndex, and Agno migrated to the same gateway boundary;
- [x] MCP v2 compatibility and real local STDIO host/client smoke;
- [x] framework-neutral content-free logical OpenTelemetry observation contract;
- [x] immutable Phase 15 provider-backed final evaluation tied to the exact evaluated Git commit;
- [x] strict provider-free local/CI quality gate.

Candidate next experiments:

- [ ] investigate the separate LlamaIndex synchronous-call timeout behavior tracked in issue #61;
- [ ] extend MCP from compatibility smoke into explicit tool authorization and least-privilege experiments;
- [ ] evaluate deployment-owned gateway retry/fallback, budgets, and scoped client credentials as separate governed policies;
- [ ] compose deployment-grade OpenTelemetry providers/exporters without moving content into logical telemetry;
- [ ] add controlled human-in-the-loop workflows;
- [ ] increase sample sizes for latency distributions and uncertainty estimates;
- [ ] evaluate provider/model variation behind the stable gateway alias.

## Why this project exists

Agentic frameworks make impressive demos easy to build. The harder problem is designing systems where probabilistic reasoning can be constrained, validated, measured, audited, recovered, compared, and safely replaced.

This repository treats framework choice as an implementation detail beneath a stable security boundary and uses reproducible evidence to study the tradeoffs.
