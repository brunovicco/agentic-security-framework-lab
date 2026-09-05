# Final Evaluation Evidence Workflow

## Purpose

Phase 15 evaluates the current repository state after the framework runtimes have been centralized behind the LiteLLM gateway and after the shared logical observability boundary has been completed.

The earlier five-way benchmark remains valid historical evidence. It must not be rewritten merely because the architecture evolved after that run.

The final evaluation therefore reuses the existing benchmark entry points while changing only their execution workspace and evidence destination.

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

## Gateway and secret handling

The final evaluation uses the existing gateway environment contract. It verifies that the gateway endpoint and client credential are configured but never prints their values.

`AGENTIC_LAB_MODEL` is removed from child-process environments so the obsolete direct-provider selector cannot influence the proof. Agno vendor telemetry remains disabled through `AGNO_TELEMETRY=false`.

No provider credential is stored in the final-evaluation bundle.

## Running the evaluation

With the existing LiteLLM gateway already configured and available:

```bash
uv run python scripts/run_final_evaluation.py
```

An explicit immutable run identifier may be supplied when useful:

```bash
uv run python scripts/run_final_evaluation.py --run-id phase15-20260905
```

Provider-backed final evaluation is intentionally not part of normal CI. The repository quality gate must remain provider-free and must not require external provider credentials.

## What this evidence proves

A successful final-evaluation bundle proves that the five current framework entry points can execute the shared evaluation workload under the current committed gateway boundary and can still produce mutually comparable benchmark artifacts.

It does not prove statistical significance, production latency SLOs, broad prompt-injection resistance, or production OpenTelemetry exporter readiness.

OpenTelemetry provider, processor, exporter, and collector configuration remains a deployment composition concern and is not required to establish benchmark comparability.
