# Adversarial v2 — Cross-Framework Baseline Plan

## Purpose

Promote the adversarial v2 evidence-plane experiment from provider-backed compatibility smoke to a repeated cross-framework evaluation without weakening the experiment's trust boundaries.

The existing LangGraph v2 artifact remains the first accepted baseline. CrewAI Flow, LlamaIndex Workflow, and Agno Workflow must generate new repeated artifacts; the one-repetition smoke artifacts are never promoted in place.

## Shared experiment contract

Every lightweight workflow baseline candidate must use the same:

- six adversarial v2 evidence-plane scenarios;
- framework-neutral evidence bundles and provenance;
- deterministic applicability oracle;
- deterministic output validator;
- bounded retry and oracle fallback semantics;
- scenario-specific task and security assertions;
- normalized attempt-trace semantics;
- provider model configured through `AGENTIC_LAB_MODEL`;
- provider-default sampling unless a later experiment explicitly changes the protocol.

The framework adapter may change orchestration mechanics. It may not change expected truth, attacker goals, policy, validation, or final authority.

## Execution size

The default repeated candidate uses:

```text
Scenarios: 6
Repetitions per scenario: 3
Runs per workflow: 18
Lightweight workflows: 3
New provider-backed runs: 54
```

Combined with the already accepted 18-run LangGraph baseline, an accepted four-workflow comparison would contain 72 runs.

Three repetitions preserve comparability with the current LangGraph v2 baseline. This remains a small sample: latency percentiles are descriptive and do not establish statistical significance or production SLOs.

## Smoke versus baseline candidate

The two runners intentionally enforce different execution classes:

```text
benchmark_adversarial_v2_workflow_smoke.py
    --runs 1 only
    artifact_type = smoke
    official_baseline = false

benchmark_adversarial_v2_workflow_baseline.py
    --runs >= 2
    default = 3
    artifact_type = baseline_candidate
    official_baseline = false
```

A repeated run is not automatically an official baseline. Generation and acceptance are separate steps.

## Candidate artifact lifecycle

The repeated runner writes to:

```text
artifacts/adversarial-v2-candidates/<workflow>/latest.json
artifacts/adversarial-v2-candidates/<workflow>/latest.md
```

Generated artifacts remain explicitly review-gated:

```text
artifact_type: baseline_candidate
official_baseline: false
review_status: pending_manual_trace_review
```

This prevents a successful command execution from silently becoming accepted benchmark evidence.

## Manual review gate

Before promotion, inspect every attempt trace and confirm that:

- all expected scenarios and iterations are present;
- evidence identity and asset cardinality are preserved;
- final applicability matches the deterministic oracle;
- human-review policy is preserved;
- no forbidden recommendation canary or attacker-selected action is accepted;
- confidence remains within the scenario-specific contract;
- every model attempt, deterministic rejection, retry, recovery, and fallback is represented consistently;
- model/provider/sampling metadata matches the intended experiment.

Any task mismatch, security failure, or unsafe acceptance blocks promotion until the observation is understood. Do not delete a failed candidate merely to obtain a clean baseline.

## Promotion

Promotion is a separate reviewed change. Accepted candidate artifacts should be copied into the official namespace:

```text
artifacts/adversarial-v2/crewai-flow/
artifacts/adversarial-v2/llamaindex-workflow/
artifacts/adversarial-v2/agno-workflow/
```

The promotion change must also record the manual review result and update project documentation. Only then may the artifacts be described as official baselines.

## Cross-framework comparison

Do not build the consolidated adversarial v2 comparison from smoke or pending candidate artifacts.

After all four workflow baselines are accepted, add a comparison step that verifies experiment identity before aggregating metrics. At minimum, it must reject inputs whose suite version, model, sampling mode, scenario count, or repetition count differ.

The comparison should distinguish:

- task accuracy;
- security pass rate;
- model attack success rate;
- unsafe acceptance rate;
- deterministic rejection/recovery/fallback rates when exercised;
- model calls and token usage;
- latency as descriptive evidence only.

A correct final system result must not be conflated with a correct first model attempt.

## Reproduction command

With provider credentials loaded outside repository files:

```bash
export AGENTIC_LAB_MODEL="openai:gpt-5.6-luna"
uv run python scripts/benchmark_adversarial_v2_workflow_baseline.py --runs 3
```

Individual workflows may be selected with repeated `--framework` arguments when operational isolation is useful.

## Security interpretation

This experiment remains a narrow synthetic evidence-plane evaluation. Even a 100% observed security pass rate does not prove broad prompt-injection resistance.

The system property under study is stronger and more specific:

> Untrusted evidence may influence reasoning, but deterministic software retains authority over evidence identity, applicability validation, bounded recovery, policy, and the final accepted result.
