# Adversarial v2 official baseline comparison

## Purpose

This comparison is a provider-free reporting layer over already accepted adversarial v2 baseline evidence. It does not call a model, re-run a framework, or reinterpret raw scenario outputs.

Its job is narrower: prove that the persisted baselines are comparable before placing their metrics side by side.

## Comparison contract

The comparator fails closed unless all four expected baselines are present in this exact evidence set:

- LangGraph evaluator-optimizer
- CrewAI Flow
- LlamaIndex Workflow
- Agno Workflow

Every baseline must agree on:

- schema version `1`
- adversarial suite version `2`
- model `openai:gpt-5.6-luna`
- sampling `provider_default`
- three repetitions per scenario
- six scenarios
- 18 runs per baseline
- passing baseline assessment with no recorded failures

A mismatch means the artifacts do not represent the same experiment and must not be compared.

## Acceptance provenance

CrewAI Flow, LlamaIndex Workflow, and Agno Workflow use the current promotion contract. Each artifact must be:

- `artifact_type = baseline`
- `official_baseline = true`
- `review_status = accepted_manual_trace_review`
- linked to a persisted source-candidate SHA-256 through promotion provenance

LangGraph is a historical exception. Its adversarial v2 baseline was accepted before the promotion metadata existed. Rewriting that evidence would blur provenance, so the comparator instead pins the exact historical Git blob:

```text
5c16cd9601ba737947a69627430431dd343f3181
```

Any byte change to the legacy artifact causes comparison to fail closed.

## Reported dimensions

The report keeps these dimensions separate rather than collapsing them into one score:

- task accuracy
- security pass rate
- model attack success rate
- unsafe acceptance rate
- deterministic rejection after attack
- recovery after rejection
- control containment
- retry rate
- fallback rate
- mean, p50, and p95 latency
- mean and total tokens

Containment metrics are conditional on a model attack actually occurring. In the accepted canonical baseline set, no live model attack succeeded, so those rates remain unexercised rather than being interpreted as zero effectiveness.

## Interpretation boundary

The comparison does not declare a framework winner.

All four accepted baselines achieved the same observed task and security outcome in this six-scenario suite. Latency and token differences are descriptive only because the sample is small and provider variance is material. The Agno baseline also contains a 10.151-second latency outlier, which makes ranking from these runs especially inappropriate.

The separate LangGraph sensitivity control remains the evidence that deterministic rejection and fallback containment work after deliberately inducing model attack success.
