# ADR 0011: Uncertain external side effects: idempotency and reconciliation

- **Status:** Accepted — `external_side_effect_state=unknown` remains terminal in lab scope
- **Date:** 2026-09-06
- **Scope:** `ActionExecutionFailureEvidence`, `GovernedActionExecutionError`, mutable executor port
- **Related:** `docs/ARCHITECTURE.md` §7, §15

## Context

When an authorized executor raises after invocation, the runtime produces typed
failure evidence with `execution_attempted=true`, `failure_reason=executor_error`,
and `external_side_effect_state=unknown`. The lab deliberately refuses to infer
rollback, compensation, or transactional state from an exception.

That refusal is correct and is one of the strongest honesty properties in the
project. It is also terminal: nothing in the system can ever move a record out of
`unknown`. Each such failure permanently deposits an unresolved fact.

Two things are worth separating. In the current controlled adapter the side effect
is in-memory, so `unknown` is a *modelled* state, not an *observed* one — the
fixture can see there was no mutation and the runtime still records `unknown`, on
purpose. Against a real external system, `unknown` would be genuine, and the
absence of a resolution path would become an operational problem rather than a
modelling choice.

## Decision

Keep `unknown` terminal. Do not implement idempotency keys, executor probing, or a
reconciliation worker in the current scope. Record the design so that the terminal
state is a declared boundary of a lab with no external side effects, not an
unexamined dead end.

The governing reason for deferral: reconciliation implemented against an in-memory
adapter would be a simulation of reconciliation. It would always succeed, exercise
no real indeterminacy, and produce evidence that proves nothing — the failure mode
this repository exists to argue against.

## Design of record

**Idempotency key.** Derived deterministically before executor invocation:

```
idempotency_key = SHA-256(
    caller_id || identity_source || action || resource || environment || approval_id_or_proposal_nonce
)
```

It must be established *before* the executor is reached and passed to the executor,
because a key computed after a failure cannot be correlated with whatever the
external system may have already recorded. This ordering is the part that is
awkward to retrofit; everything else here is additive.

**Executor probe capability.** The mutable executor port gains an optional
`probe(idempotency_key)` returning `committed | not_committed | indeterminate`.
Optional matters: an executor that cannot be probed is a legitimate case, and for
that executor `unknown` stays terminal by construction. Reconciliation is a
property of the downstream system, not something the runtime can impose on it.

**Reconciliation as new evidence, never mutation.** A reconciliation worker
resolves outstanding records and writes a *new linked record*:

```
unknown → resolved_committed
        → resolved_not_committed
        → permanently_indeterminate   (after bounded attempts)
```

The original failure evidence is never rewritten. This preserves the property the
repository already holds for benchmark artifacts: history is appended to, not
corrected.

**Interaction with claimed approval.** A `not_committed` outcome does **not**
restore already-claimed single-use approval authority. Retrying requires new
approval. This is a policy choice, not a technical necessity, and it should be
stated explicitly rather than emerge from implementation: restoring approval on
inferred non-commitment would make approval authority a function of a probe result,
which is precisely the kind of authority leakage the project rejects elsewhere.

**Ordering guarantee.** Reconciliation must not run concurrently with a retry of
the same key against the same executor, or the probe races the retry. Serialization
per `idempotency_key` is a requirement, not an optimization.

## Consequences

- The lab keeps an honest terminal state and an explicit reason for it.
- Two ordering constraints that would be expensive to retrofit — key established
  pre-invocation, per-key serialization — are now recorded before any external
  executor exists.
- Documentation can state that non-resolution is a scope boundary rather than an
  oversight.

## Revisit triggers

- Any executor with a real external side effect is introduced.
- Evidence gains persistence, making outstanding `unknown` records accumulate
  across runs.
- A downstream system offers idempotency semantics the runtime could use.

## Alternatives considered

**Retry on executor failure.** Converts an unknown side-effect state into a
possible duplicate one. Strictly worse, and it is the reason framework retries are
already suppressed around mutable executors. Rejected.

**Treat an exception as non-commitment.** The most common real-world shortcut and
the one this project exists to reject. An exception says the runtime did not
receive confirmation; it says nothing about what the external system did. Rejected.

**Implement reconciliation now against the in-memory adapter.** No indeterminacy to
resolve, no negative test possible. Rejected.
