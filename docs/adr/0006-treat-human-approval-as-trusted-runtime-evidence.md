# ADR 0006: Treat human approval as trusted runtime evidence

## Status

Accepted

## Context

The governed action runtime can receive deterministic authorization outcomes of `allow`, `deny`, or `require_human_approval`.

Before this decision, `require_human_approval` was correctly blocking: it never reached the executor. The next requirement is to support a controlled human-in-the-loop path without turning approval into model-generated content, a free-form prompt claim, or an override for explicit policy denial.

The project already separates untrusted `ProposedAction` from trusted `ActionContext`. Human approval needs the same trust discipline.

A later hardening review identified an additional requirement: trusted approval evidence for a mutable action must not be reusable indefinitely. A reusable lookup would allow one human decision to authorize repeated identical side effects.

After the single-use capability model was in place, a second temporal gap remained: an approval that had never been claimed could stay valid indefinitely. Old human intent must not authorize a much later mutable side effect merely because the approval was still unused.

After freshness was enforced, a third lifecycle gap remained: a still-valid approval could not be explicitly withdrawn before use. Trusted control-plane intent needs a way to revoke an unused capability without turning revocation into model input or rewriting authorization policy.

## Decision

Human approval is represented as separate trusted application evidence.

`HumanApprovalEvidence` is bound to:

- one exact `ProposedAction`;
- one exact trusted `ActionContext`;
- a synthetic approval identifier;
- a synthetic approver identifier;
- one timezone-aware issuance instant `approved_at`;
- one timezone-aware exclusive expiry instant `expires_at`.

The identifiers are useful local audit evidence in this lab, but they are not authentication or IAM attestations.

`ActionApprovalProvider` is the framework-neutral port used by `GovernedActionRuntime` to **claim** approval evidence. The default provider returns no approval, so an application that does not configure a trusted HITL source remains fail-closed.

The port exposes `claim_approval(...)`, not a reusable read operation. It returns an explicit `ApprovalClaim` with `missing`, `claimed`, or `revoked` status. A successful `claimed` result transfers one unused approval capability to one runtime attempt. The controlled in-memory provider removes that queued capability from future claims, so the same evidence cannot be replayed.

`ActionApprovalRevoker` is a separate trusted control-plane port. It can revoke one exact `approval_id` only while that capability is still unclaimed. Revocation does not mutate `HumanApprovalEvidence`, does not come from `ProposedAction`, and does not override deterministic authorization policy.

The runtime consults approval evidence only when deterministic policy returns `require_human_approval`.

The runtime then records one of seven low-cardinality approval states:

```text
not_applicable
missing
invalid
not_yet_valid
expired
revoked
validated
```

A matching approval must also be valid at the runtime's trusted current time. Only `validated` evidence satisfies the runtime precondition and permits execution while preserving the original authorization outcome `require_human_approval` in execution evidence.

An explicit `deny` is terminal. The approval provider is not consulted for denied actions, so human approval cannot override policy denial. Normal `allow` outcomes also do not claim approval.

The runtime defensively checks that claimed approval evidence matches the exact proposed action and trusted caller context. A provider returning approval for another scope therefore fails closed even if the provider itself is buggy.

### Temporal validity

Approval validity uses the half-open interval:

```text
[approved_at, expires_at)
```

The evidence model requires timezone-aware timestamps and rejects `expires_at <= approved_at`. `GovernedActionRuntime` owns freshness enforcement through an injected `ApprovalClock`; the approval provider does not decide whether evidence is temporally valid. Production composition uses a UTC clock while tests inject deterministic fixed time.

If trusted current time is before `approved_at`, the runtime records `not_yet_valid`. If current time is equal to or later than `expires_at`, it records `expired`. Both outcomes block execution. A clock returning a naive datetime is rejected as an invalid trusted temporal boundary.

Temporal validation happens only after policy requires HITL, one approval has been claimed, and exact action/context binding has been confirmed. Normal `allow`, terminal `deny`, missing approval, and scope-mismatch paths therefore do not depend on time unnecessarily.

A future-dated or expired approval is already claimed when temporal failure is discovered, so it stays consumed. Retry requires fresh human evidence rather than waiting for or resurrecting the same capability.

### Explicit revocation

A valid, unused approval is not irrevocable authority. Trusted control-plane code may call `revoke_approval(approval_id)` before claim. The controlled provider changes that capability from `available` to `revoked`; repeated revocation attempts return false instead of manufacturing new lifecycle state.

When the revoked capability reaches its exact queued claim position, `claim_approval(...)` returns `ApprovalClaim(status="revoked", approval=...)`. `GovernedActionRuntime` preserves the original `require_human_approval` policy decision, records approval status `revoked`, and blocks before consulting approval time or invoking the mutable executor. The revoked capability is then absent from later claims, so retry receives `missing` unless another distinct approval exists.

Revocation is deliberately pre-claim only. Once a capability has already been claimed, `revoke_approval(...)` returns false and cannot retroactively cancel the runtime attempt to which authority was transferred. Solving cancellation after claim would require a different coordination model and is outside this process-local experiment.

Revocation targets immutable approval identity, not broad action scope. Revoking one approval does not revoke a second distinct approval for the same action/context.

### Single-use and failure semantics

Approval is consumed when it is claimed, before the mutable executor runs.

This is intentionally fail-closed. If claimed evidence is invalid, or if the executor fails after a valid claim, the approval is not restored automatically. A retry requires a new human approval.

This avoids a dangerous ambiguity where a failed or partially failed mutable execution could silently replay the same authorization capability.

The in-memory provider can hold multiple **distinct** approvals for the same exact action scope. That models two deliberately approved executions without reusing the same approval. Duplicate `approval_id` values are rejected by the fixture.

The lab does not claim distributed transactional atomicity between approval storage and an external side effect; that remains outside the controlled in-memory experiment.

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

Each approval is a single-use capability with process-local lifecycle state `available`, `revoked`, or `claimed`. A matching claim removes that queued capability from future use. Multiple unique approvals may be supplied for the same scope when multiple independent executions were separately approved.

The fixture proves trust-boundary and anti-replay mechanics; it is not production HITL infrastructure.

## Alternatives considered

### Put `approved=true` in `ProposedAction`

Rejected because the proposal is model-adjacent and untrusted. The proposer cannot manufacture the evidence needed to satisfy its own approval requirement.

### Treat approval text in evidence as authoritative

Rejected because statements such as `SOC Manager approved this action` are untrusted content until validated by a trusted approval source.

### Keep approval as a reusable lookup

Rejected because one human approval could then authorize an unbounded number of identical mutable executions. Approval is modeled as a consumable capability instead.

### Convert `require_human_approval` to `allow` after approval

Rejected because it destroys information about the original policy requirement and makes authorization decisions harder to distinguish from approval satisfaction.

### Allow human approval to override `deny`

Rejected. Approval is an additional precondition for approval-gated policy, not a policy bypass mechanism.

### Restore approval automatically after executor failure

Rejected because the external side effect may have partially occurred before failure became visible. Automatic restoration would permit an ambiguous retry with the same approval capability.

### Add a database, workflow engine, or identity provider now

Rejected because the current increment only needs to prove trusted approval separation, exact binding, single-use semantics, and runtime enforcement.

## Consequences

### Positive

- missing approval remains fail-closed;
- approval cannot be forged inside the model proposal schema;
- approvals are exact-scope and principal-bound;
- one approval cannot be replayed for repeated mutable executions;
- explicit deny stays terminal;
- normal allow does not consume HITL evidence;
- executor failure does not silently restore an already claimed approval;
- trusted control-plane code can withdraw one still-unclaimed approval without exposing revocation to model-controlled inputs;
- revoked approval is distinguishable from missing, invalid, expired, and validated evidence;
- authorization outcome, approval status, and execution occurrence remain independently observable;
- frameworks continue consuming the governed runtime without duplicating HITL policy.

### Trade-offs

- synthetic approver identity is not authentication proof;
- durable approval persistence, durable/distributed revocation, and multi-party approval are not modeled yet;
- process-local revocation cannot retroactively cancel an approval after its capability has been claimed;
- temporal validity is enforced locally, but this does not prove clock synchronization or distributed expiry enforcement across processes;
- the in-memory claim operation is process-local and does not prove distributed transactional atomicity;
- the in-memory provider is controlled lab infrastructure only.

Those omissions are deliberate. They should be introduced only when a concrete experiment needs them.

## Observability

This phase does not emit approval identifiers or approver identifiers through OpenTelemetry.

If approval telemetry is added later, prefer low-cardinality logical fields such as approval status and whether approval was required. Human comments, identifiers, credentials, tokens, and other sensitive/high-cardinality values remain outside default telemetry.

## Security invariant

```text
model claim of approval != trusted human approval

policy deny + human approval = deny

require_human_approval + missing/invalid/not-yet-valid/expired/revoked approval = no execution

valid + unused approval != irrevocable authority

revoked unclaimed approval = no execution

valid approval time = approved_at <= trusted_now < expires_at

one claimed approval = at most one execution attempt

consumed approval + retry = new approval required
```

Refs #131, #145, #163, #165
