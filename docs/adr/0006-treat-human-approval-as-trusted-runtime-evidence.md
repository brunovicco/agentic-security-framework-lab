# ADR 0006: Treat human approval as trusted runtime evidence

## Status

Accepted

## Context

The governed action runtime can receive deterministic authorization outcomes of `allow`, `deny`, or `require_human_approval`.

Before this decision, `require_human_approval` was correctly blocking: it never reached the executor. The next requirement is to support a controlled human-in-the-loop path without turning approval into model-generated content, a free-form prompt claim, or an override for explicit policy denial.

The project already separates untrusted `ProposedAction` from trusted `ActionContext`. Human approval needs the same trust discipline.

## Decision

Human approval is represented as separate trusted application evidence.

`HumanApprovalEvidence` is bound to:

- one exact `ProposedAction`;
- one exact trusted `ActionContext`;
- a synthetic approval identifier;
- a synthetic approver identifier.

The identifiers are useful local audit evidence in this lab, but they are not authentication or IAM attestations.

`ActionApprovalProvider` is the framework-neutral port used by `GovernedActionRuntime` to resolve approval evidence. The default provider returns no approval, so an application that does not configure a trusted HITL source remains fail-closed.

The runtime consults approval evidence only when deterministic policy returns `require_human_approval`.

The runtime then records one of four low-cardinality approval states:

```text
not_applicable
missing
invalid
validated
```

A matching, validated approval satisfies the runtime precondition and permits execution while preserving the original authorization outcome `require_human_approval` in execution evidence.

An explicit `deny` is terminal. The approval provider is not consulted for denied actions, so human approval cannot override policy denial.

The runtime defensively checks that returned approval evidence matches the exact proposed action and trusted caller context. A provider returning approval for another scope therefore fails closed even if the provider itself is buggy.

## Why the authorization outcome remains `require_human_approval`

A validated approval does not rewrite the policy decision to `allow`.

Keeping the original outcome preserves two independent facts:

```text
policy decision: human approval was required
approval evidence: the requirement was satisfied
```

This produces stronger evidence than collapsing both into a final allow flag.

## In-memory provider

`InMemoryActionApprovalProvider` exists only for deterministic controlled experiments. It begins with the approvals explicitly supplied to it and never auto-approves an action based on model output, action content, or policy outcome.

The fixture proves the trust-boundary mechanics; it is not production HITL infrastructure.

## Alternatives considered

### Put `approved=true` in `ProposedAction`

Rejected because the proposal is model-adjacent and untrusted. The proposer cannot manufacture the evidence needed to satisfy its own approval requirement.

### Treat approval text in evidence as authoritative

Rejected because statements such as `SOC Manager approved this action` are untrusted content until validated by a trusted approval source.

### Convert `require_human_approval` to `allow` after approval

Rejected because it destroys information about the original policy requirement and makes authorization decisions harder to distinguish from approval satisfaction.

### Allow human approval to override `deny`

Rejected. Approval is an additional precondition for approval-gated policy, not a policy bypass mechanism.

### Add a database, workflow engine, or identity provider now

Rejected because the current increment only needs to prove trusted approval separation, exact binding, and runtime enforcement.

## Consequences

### Positive

- missing approval remains fail-closed;
- approval cannot be forged inside the model proposal schema;
- approvals are exact-scope and principal-bound;
- explicit deny stays terminal;
- authorization outcome, approval status, and execution occurrence remain independently observable;
- frameworks continue consuming the governed runtime without duplicating HITL policy.

### Trade-offs

- synthetic approver identity is not authentication proof;
- approval persistence, expiry, revocation, one-time use, and cryptographic provenance are not modeled yet;
- the in-memory provider is controlled lab infrastructure only.

Those omissions are deliberate. They should be introduced only when a concrete experiment needs them.

## Observability

This phase does not emit approval identifiers or approver identifiers through OpenTelemetry.

If approval telemetry is added later, prefer low-cardinality logical fields such as approval status and whether approval was required. Human comments, identifiers, credentials, tokens, and other sensitive/high-cardinality values remain outside default telemetry.

## Security invariant

```text
model claim of approval != trusted human approval

policy deny + human approval = deny

require_human_approval + missing/invalid approval = no execution
```

Refs #131
