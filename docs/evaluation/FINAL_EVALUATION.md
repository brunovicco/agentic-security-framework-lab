# Final Evaluation Evidence Workflow

## Purpose

Phase 15 evaluates the current repository state after the framework runtimes have been centralized behind the LiteLLM gateway and after the shared logical observability boundary has been completed.

The earlier five-way benchmark remains valid historical evidence. It must not be rewritten merely because the architecture evolved after that run.

The final evaluation therefore reuses the existing benchmark entry points while changing only their execution workspace and evidence destination.

## Completed Phase 15 evidence

The accepted provider-backed Phase 15 run is persisted immutably at:

```text
artifacts/final-evaluation/phase15-20260905-v2/
```

Its manifest records:

- evaluated commit: `dd48c2490fc4ec1c76093577f7944d76a6fbc572`;
- governed client-facing model alias: `security-analysis`;
- three repetitions per scenario;
- five framework variants and the consolidated five-way comparison.

The evidence was merged by PR #106. All five variants reached 100% expected accuracy across 75 framework executions. The run made 76 model calls because LlamaIndex `product-mismatch` iteration 1 exercised two bounded analysis attempts and then the shared deterministic oracle fallback. That anomaly is intentionally preserved as evidence rather than normalized away.

The successful rerun produced no CrewAI proprietary trace prompt, trace link, or trace batch. The final-evaluation composition explicitly disables CrewAI proprietary tracing/telemetry/tracking, including the pinned first-execution collection path, while leaving project-owned OpenTelemetry independent.

Canonical Phase 15 evidence:

- [`manifest.json`](../../artifacts/final-evaluation/phase15-20260905-v2/manifest.json)
- [five-way human-readable comparison](../../artifacts/final-evaluation/phase15-20260905-v2/benchmarks/comparison/five-way-latest.md)
- [five-way machine-readable comparison](../../artifacts/final-evaluation/phase15-20260905-v2/benchmarks/comparison/five-way-latest.json)

## Execution boundary

```text
clean committed repository
        |
        v
temporary workspace
        |
        +--> LangGraph benchmark -----------+
        +--> CrewAI Agent/Crew benchmark ---+
        +--> CrewAI Flow benchmark ---------+--> five-way comparison
        +--> LlamaIndex Workflow benchmark -+
        +--> Agno Workflow benchmark -------+
                                              |
                                              v
                                  contract validation
                                              |
                                              v
                       artifacts/final-evaluation/<run-id>/
```

Each benchmark still owns its framework-specific runtime and measurement logic. The final-evaluation runner does not duplicate or reinterpret those semantics.

Running from a temporary working directory is deliberate. The existing scripts write relative paths such as `artifacts/benchmarks/langgraph/latest.json`; isolation means those writes cannot replace the historical repository artifacts.

## Fixed comparability contract

A final run requires:

- five orchestration variants;
- the same five framework-neutral scenarios;
- three repetitions per scenario;
- 15 executions per variant;
- 75 executions across the five variants;
- the same governed client-facing model alias: `security-analysis`;
- the existing shared expected truth, deterministic validation, bounded retry, oracle fallback, and human-review policy.

The runner fails closed if any generated benchmark or the consolidated comparison reports another model identifier or repetition count.

The alias is intentionally validated instead of a provider-native model identifier. Provider/model mapping belongs behind the gateway boundary and is versioned separately in repository configuration.

## Provenance and immutability

A persisted final-evaluation bundle contains:

```text
artifacts/final-evaluation/<run-id>/
├── manifest.json
└── benchmarks/
    ├── langgraph/
    ├── crewai/
    ├── crewai-flow/
    ├── llamaindex-workflow/
    ├── agno-workflow/
    └── comparison/
```

`manifest.json` records only safe execution metadata:

- schema version;
- UTC generation time;
- full evaluated Git commit SHA;
- governed model alias;
- repetition count;
- validated JSON artifact paths.

The destination is append-only by contract: an existing `run-id` is never overwritten. Run identifiers are also validated before they are used as filesystem paths.

The manifest does not capture prompts, model responses, evidence content, rationale, evaluator feedback, asset/CVE identifiers, credentials, tokens, API keys, or provider payloads.

## Repository state

The runner requires a clean committed Git worktree before any provider-backed execution starts. This makes the recorded SHA an unambiguous statement about the exact code and versioned gateway configuration being evaluated.

Generated final evidence makes the worktree dirty only after the benchmark completes, which is expected: the evidence can then be reviewed and committed in a dedicated follow-up change.

## Gateway, telemetry, and secret handling

The final evaluation uses the existing gateway environment contract. It verifies that the gateway endpoint and client credential are configured but never prints their values.

`AGENTIC_LAB_MODEL` is removed from child-process environments so the obsolete direct-provider selector cannot influence the proof. The final-evaluation child environment also disables CrewAI proprietary tracing/telemetry/tracking and Agno vendor telemetry. It deliberately does **not** set `OTEL_SDK_DISABLED`, because project-owned OpenTelemetry remains a separate logical observability boundary.

No provider credential is stored in the final-evaluation bundle.

## Running a new evaluation

With the existing LiteLLM gateway already configured and available:

```bash
uv run python scripts/run_final_evaluation.py
```

The runner generates a new UTC run identifier by default. An explicit immutable identifier may be supplied when useful, but an existing identifier cannot be reused:

```bash
uv run python scripts/run_final_evaluation.py --run-id <new-run-id>
```

Do not reuse `phase15-20260905-v2`; that identifier belongs to the accepted immutable Phase 15 evidence.

Provider-backed final evaluation is intentionally not part of normal CI. The repository quality gate must remain provider-free and must not require external provider credentials.

## What this evidence proves

The accepted Phase 15 bundle proves that the five current framework entry points executed the shared evaluation workload under the committed centralized gateway boundary and produced mutually comparable benchmark artifacts.

It also demonstrates the difference between model quality and system safety: one LlamaIndex execution failed deterministic validation on both allowed LLM attempts, yet the application-owned oracle fallback preserved the expected final result.

It does not prove statistical significance, production latency SLOs, broad prompt-injection resistance, a universal framework ranking, or production OpenTelemetry exporter readiness.

The `security-analysis` alias proves the client-facing governed identity requested by each framework. It is not independent attestation of the provider-native model selected behind the gateway.

OpenTelemetry provider, processor, exporter, and collector configuration remains a deployment composition concern and is not required to establish benchmark comparability.
