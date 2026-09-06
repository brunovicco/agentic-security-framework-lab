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

After source-aware lifecycle isolation, one process-local concurrency gap remained: claim and revocation were compound operations across approval queues and lifecycle state without an explicit synchronization boundary. Sequential anti-replay semantics are insufficient when multiple runtime attempts can race for the same capability.

After the lifecycle was hardened, a separate authority gap remained: trusted approval evidence identifies an `approver_id`, but provenance from a trusted approval source does not prove that this human is entitled to approve every caller/action scope. Approver identity evidence and approver authorization must remain distinct.

After approver entitlement was separated, one audit-integrity gap remained: the runtime emitted valid combinations, but its Pydantic evidence models still allowed callers to construct or deserialize security states the runtime itself could never legally produce. Security evidence needs structural state-machine validation in addition to correct runtime control flow.

After successful and blocked evidence states became structurally constrained, executor failure remained an observability gap. An executor can raise after the runtime has already established caller authority and, on HITL paths, consumed a valid approval. The exception alone loses that authority chain, while treating the failure as `execution_occurred=false` would incorrectly imply that no external effect occurred.

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

The runtime then records one of eight low-cardinality approval states:

```text
not_applicable
missing
invalid
unauthorized_approver
not_yet_valid
expired
revoked
validated
```

A matching approval must also be valid at the runtime's trusted current time. Only `validated` evidence satisfies the runtime precondition and permits execution while preserving the original authorization outcome `require_human_approval` in execution evidence.

An explicit `deny` is terminal. The approval provider is not consulted for denied actions, so human approval cannot override policy denial. Normal `allow` outcomes also do not claim approval.

The runtime defensively checks that claimed approval evidence matches the exact proposed action and trusted caller context. A provider returning approval for another scope therefore fails closed even if the provider itself is buggy.

The controlled in-memory provider also partitions approval queues by the full source-aware key `(caller_id, identity_source, action, resource, environment)`. This prevents a request under one trusted identity provenance from dequeuing or consuming approval evidence issued for the same caller id and action scope under another provenance. Runtime exact-context validation remains in place as defense in depth rather than being replaced by provider indexing.

The provider serializes its queue mutation and lifecycle-state transition with one process-local lock. `claim_approval(...)` therefore removes one queued capability and marks it claimed as one linearizable operation; `revoke_approval(...)` uses the same boundary. Concurrent callers can observe either claim-first or revoke-first ordering, but they cannot reuse one approval or produce contradictory lifecycle state inside one provider instance.

### Independent approver authorization

A claimed approval is trusted evidence that a human decision was recorded; it is not by itself proof that the named human may approve the requested scope. `ActionApproverAuthorizer` is therefore a separate application port from caller authorization and from the approval provider.

The controlled `StaticActionApproverAuthorizationPolicy` evaluates one exact key:

```text
(approver_id, caller_id, identity_source, action, resource, environment)
```

Rules are explicit `allow` or `deny`; an unknown key fails closed with `deny / no_matching_rule`. The default approver authorizer also denies, so configuring trusted approval evidence without approver policy cannot silently grant global approval authority. There are no wildcards, role inheritance, nearest-match rules, or model-generated approver decisions.

`GovernedActionRuntime` consults approver authorization only after deterministic caller policy requires HITL, one approval has been claimed, exact action/context binding has passed, and the capability is not revoked. A deny records `unauthorized_approver` and blocks before freshness or mutable execution. Because the capability was already claimed, retry requires fresh human evidence rather than reusing approval from an unauthorized approver.

This ordering preserves independent facts:

```text
caller authorization != trusted approval evidence != approver authorization
```

Normal caller `allow`, caller `deny`, missing approval, invalid binding, and revoked approval paths do not consult approver authorization unnecessarily. Time validation is reached only after an explicit approver allow.

The current approver identifier remains synthetic trusted lab evidence, not human authentication. This phase proves deterministic entitlement separation; it does not claim OIDC/workforce IAM, directory-backed roles, signed human attestations, self-approval controls, or multi-party/quorum workflow.

### Evidence state-machine integrity

`AuthorizationDecision` and `ActionExecutionEvidence` are security evidence, not loose transport DTOs. They therefore reject combinations that deterministic policy and `GovernedActionRuntime` cannot legally emit.

Caller authorization reason is bound to outcome: `allow` requires `explicit_allow`; `require_human_approval` requires `human_approval_required`; `deny` permits only `explicit_deny` or fail-closed `no_matching_rule`.

Execution evidence then validates the complete control path. Caller `deny` is non-executing with `not_applicable` approval state. Direct caller `allow` carries no HITL evidence and represents completed direct execution. Approval-gated evidence cannot use `not_applicable`; `missing`, `invalid`, `revoked`, `unauthorized_approver`, `not_yet_valid`, `expired`, and `validated` each require the exact human evidence, approver decision, binding relationship, and execution flag associated with that runtime state. Only `validated` may record execution on the HITL path.

This hardening protects audit, serialization, and replay consumers from accepting records such as `deny + execution_occurred=true` or `validated` without exact-bound human evidence and approver allow. It does not make records cryptographically tamper-proof and does not prove that an external storage system cannot replace a whole record.

```text
security evidence must not represent a state the governed runtime could never legally produce
```

### Executor failure evidence

Crossing the executor boundary is not equivalent to proving a successful external side effect. If an authorized executor raises, `GovernedActionRuntime` raises `GovernedActionExecutionError`, a `RuntimeError` subtype carrying immutable `ActionExecutionFailureEvidence`.

Failure evidence preserves the exact proposed action, trusted caller context, caller authorization, and any validated human/approver authority that permitted the attempt. It records only low-cardinality execution facts: `execution_attempted=true`, `failure_reason=executor_error`, and `external_side_effect_state=unknown`. The original executor exception is chained as the local Python cause but its raw message is not copied into structured failure evidence or the governed error message.

Direct-allow failure evidence must remain HITL-free. Approval-gated failure evidence requires an exact-bound `validated` approval plus explicit approver allow. Caller deny and blocked approval states therefore cannot manufacture executor-failure evidence because they never cross the executor boundary.

An executor exception does not prove that the external operation committed zero, partial, or complete effects before failure became visible. The runtime therefore does not map executor failure to ordinary `ActionExecutionEvidence(execution_occurred=false)`, does not restore consumed approval, and does not automatically retry.

```text
executor raised != external side effect did not occur
executor invocation + exception => external side-effect state is unknown
```

This is audit evidence for an execution attempt, not rollback, compensation, idempotency, two-phase commit, or distributed transaction semantics.

### Temporal validity

Approval validity uses the half-open interval:

```text
[approved_at, expires_at)
```

The evidence model requires timezone-aware timestamps and rejects `expires_at <= approved_at`. `GovernedActionRuntime` owns freshness enforcement through an injected `ApprovalClock`; the approval provider does not decide whether evidence is temporally valid. Production composition uses a UTC clock while tests inject deterministic fixed time.

If trusted current time is before `approved_at`, the runtime records `not_yet_valid`. If current time is equal to or later than `expires_at`, it records `expired`. Both outcomes block execution. A clock returning a naive datetime is rejected as an invalid trusted temporal boundary.

Temporal validation happens only after policy requires HITL, one approval has been claimed, exact action/context binding has been confirmed, revocation has been ruled out, and the approver has been explicitly authorized. Normal `allow`, terminal `deny`, missing approval, scope-mismatch, revoked, and unauthorized-approver paths therefore do not depend on time unnecessarily.

A future-dated or expired approval is already claimed when temporal failure is discovered, so it stays consumed. Retry requires fresh human evidence rather than waiting for or resurrecting the same capability.

### Explicit revocation

A valid, unused approval is not irrevocable authority. Trusted control-plane code may call `revoke_approval(approval_id)` before claim. The controlled provider changes that capability from `available` to `revoked`; repeated revocation attempts return false instead of manufacturing new lifecycle state.

When the revoked capability reaches its exact queued claim position, `claim_approval(...)` returns `ApprovalClaim(status="revoked", approval=...)`. `GovernedActionRuntime` preserves the original `require_human_approval` policy decision, records approval status `revoked`, and blocks before consulting approval time or invoking the mutable executor. The revoked capability is then absent from later claims, so retry receives `missing` unless another distinct approval exists.

Revocation is deliberately pre-claim only. Once a capability has already been claimed, `revoke_approval(...)` returns false and cannot retroactively cancel the runtime attempt to which authority was transferred. Solving cancellation after claim would require a different coordination model and is outside this process-local experiment.

Revocation targets immutable approval identity, not broad action scope. Revoking one approval does not revoke a second distinct approval for the same action/context.

### Process-local concurrency semantics

Single-use authority must remain single-use when multiple runtime attempts arrive concurrently. The controlled provider uses one lock for both the source-aware queue and lifecycle dictionary so compound claim/revoke transitions are serialized together rather than relying on Python interpreter scheduling details.

Tests coordinate threads with barriers instead of sleeps. Eight simultaneous claims for one approval yield exactly one `claimed` result and seven `missing` results. A claim-vs-revoke race has only two legal linearizable outcomes: claim wins and later revocation returns false, or revocation wins and the queued claim reports `revoked`. Eight concurrent approval-gated `GovernedActionRuntime` attempts with one capability produce exactly one `validated` execution and seven `missing` results.

This guarantee is intentionally process-local. The lock does not coordinate multiple processes, durable approval stores, remote workers, or an external side effect transaction. A production distributed provider would need its own atomic storage/coordination primitive while preserving the same application contract.

```text
one approval capability + concurrent claims <= one claimed runtime attempt
```

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

Each approval is a single-use capability with process-local lifecycle state `available`, `revoked`, or `claimed`. Queues are partitioned by exact caller id, identity source, action, resource, and environment. A matching source-aware claim removes that queued capability from future use. One process-local lock protects queue removal and lifecycle transitions together under concurrent claim/revoke calls. Multiple unique approvals may be supplied for the same exact source-aware scope when multiple independent executions were separately approved.

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
- approvals are exact-scope, principal-bound, and isolated by trusted identity source before claim;
- one approval cannot be replayed for repeated or concurrent mutable executions within one provider instance;
- explicit deny stays terminal;
- normal allow does not consume HITL evidence;
- executor failure does not silently restore an already claimed approval;
- authorized executor failure preserves a safe structured authority trail while keeping external side-effect state explicitly unknown;
- trusted control-plane code can withdraw one still-unclaimed approval without exposing revocation to model-controlled inputs;
- revoked approval is distinguishable from missing, invalid, expired, and validated evidence;
- caller authorization, approval lifecycle, approver authorization, and execution occurrence remain independently observable;
- frameworks continue consuming the governed runtime without duplicating HITL policy.

### Trade-offs

- synthetic approver identity is not authentication proof, and exact approver policy is not workforce IAM;
- durable approval persistence, durable/distributed revocation, and multi-party approval are not modeled yet;
- process-local revocation cannot retroactively cancel an approval after its capability has been claimed;
- temporal validity is enforced locally, but this does not prove clock synchronization or distributed expiry enforcement across processes;
- the in-memory claim/revoke lock is process-local and does not prove cross-process or distributed transactional atomicity;
- one global fixture lock favors simple correctness over parallel claim throughput and is not presented as a distributed scaling design;
- the in-memory provider is controlled lab infrastructure only.

Those omissions are deliberate. They should be introduced only when a concrete experiment needs them.

## Observability

This phase does not emit approval identifiers or approver identifiers through OpenTelemetry.

If approval telemetry is added later, prefer low-cardinality logical fields such as approval status and whether approval was required. Human comments, identifiers, credentials, tokens, and other sensitive/high-cardinality values remain outside default telemetry.

## Security invariant

```text
model claim of approval != trusted human approval

policy deny + human approval = deny

require_human_approval + missing/invalid/unauthorized-approver/not-yet-valid/expired/revoked approval = no execution

trusted approval evidence != authorized approver

caller authorization != approver authorization

valid + unused approval != irrevocable authority

revoked unclaimed approval = no execution

same caller_id + different identity_source != same approval capability

valid approval time = approved_at <= trusted_now < expires_at

one claimed approval = at most one execution attempt

one approval capability + concurrent claims <= one claimed runtime attempt

consumed approval + retry = new approval required

executor raised != external side effect did not occur

executor invocation + exception = external side-effect state unknown
```

Refs #131, #145, #163, #165, #167, #169, #174, #178
