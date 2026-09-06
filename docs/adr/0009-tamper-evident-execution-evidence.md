# ADR 0009: Tamper-evident execution evidence

- **Status:** Accepted — boundary declared, implementation deliberately out of scope
- **Date:** 2026-09-06
- **Scope:** `ActionExecutionEvidence`, `ActionExecutionFailureEvidence`, authenticated variants
- **Related:** `docs/ARCHITECTURE.md` §12, `docs/security/GOVERNED_AGENT_ACTIONS.md`

## Context

The governed runtime already separates authorization, approval lifecycle, approver
authorization, and execution as independent evidence facts. That gives the project
its core property:

```
evidence explains how a result was produced
```

It does not give this one:

```
evidence proves it was not altered afterwards
```

Today evidence is an in-process immutable value object. Immutability holds inside a
single Python process and ends there. Anything that can write to a future evidence
store can also fabricate a well-formed record, reorder records, or delete them, and
nothing in the current contracts would detect it.

For a reviewer whose real question is *"can this record have been changed after the
fact?"*, the honest current answer is: yes, and nothing here would show it.

The distinction that matters for this project is between two claims:

| Claim | Current state |
| --- | --- |
| The runtime recorded these authority facts | supported by typed contracts and conformance tests |
| These records are the ones the runtime produced | **not supported** |

## Decision

Do not implement signing, hash chaining, or tamper-evident storage in the current
lab scope. Record the intended design so the gap is a declared boundary rather than
an unexamined omission, and constrain the vocabulary used in documentation.

Concretely:

1. No cryptographic integrity mechanism is added while evidence has no persistence
   surface. Chaining in-memory records that never leave the process would produce a
   mechanism that cannot fail, i.e. evidence that proves nothing.
2. Documentation must not describe current evidence as an *audit trail*,
   *audit-grade*, *tamper-proof*, or *non-repudiable*. The permitted framing is
   *execution evidence* and *authority provenance*.
3. Any future introduction of evidence persistence triggers this ADR before the
   store is designed, not after.

## Design of record

Kept here so the deferral is a decision, not an absence.

**Canonical form.** Each evidence record is serialized deterministically —
RFC 8785 JSON Canonicalization Scheme, or an equivalent fixed field ordering with
no floats and timezone-normalized timestamps — producing `payload_bytes`. Without a
canonical form, hashes are not comparable across runtimes or language versions.

**Record hash.**

```
record_hash = SHA-256(payload_bytes)
```

**Append-only chain, per enforcement instance.**

```
chain_hash[0] = SHA-256(instance_id || genesis_constant)
chain_hash[n] = SHA-256(chain_hash[n-1] || record_hash[n] || seq[n])
```

`seq` is a monotonic counter owned by the runtime. It is never supplied by a
caller, a tool argument, or a framework adapter — the same rule that already
applies to `caller_id`.

**Checkpoints.** Periodically, a Merkle root over the window of records since the
last checkpoint is signed with a key held **outside** the application process
(KMS or HSM) and published to a store the application cannot rewrite.

**Verification.** A standalone verifier recomputes the chain from stored records
and compares it against signed checkpoints. This detects mutation, reordering, and
truncation of any window that has been checkpointed.

**What the design still does not buy.** Chain integrity is not truth. A compromised
runtime can write false-but-well-formed evidence at write time, and it will chain
and verify perfectly. Integrity protects the record after it exists; it says nothing
about whether the record was honest when created. Reducing that residual risk needs
process separation between evidence production and key custody, which is a
deployment property, not a code property.

Truncation after the most recent checkpoint remains detectable only as a gap in
`seq`, which an attacker controlling the store can also remove. Checkpoint interval
is therefore a security parameter, not a performance knob.

## Consequences

- The project keeps a defensible claim (`evidence explains`) instead of an
  indefensible one (`evidence proves`).
- Regulated-review readers get an explicit answer to their first question rather
  than silence.
- The cost of adopting this later is bounded: canonical serialization and `seq`
  ownership are the only parts that would be awkward to retrofit, and both are
  local to the evidence contracts.

## Revisit triggers

- Any evidence persistence is introduced, however small.
- An experiment requires a reviewer to trust evidence produced outside their
  control.
- Evidence crosses a process, host, or organizational boundary.

## Alternatives considered

**Sign each record individually, no chain.** Detects mutation of a record, not
deletion or reordering of the sequence. Deletion is the more realistic attack
against evidence that exonerates or incriminates. Rejected.

**Write to an append-only managed log and rely on the provider.** Moves the trust
anchor to a vendor without recording why that is acceptable. Reasonable in
production, but it would let this lab claim a property it did not construct.
Rejected for the lab; noted as the likely production answer.

**Implement the chain now against in-memory evidence.** Produces a mechanism with
no adversary, no persistence, and no possible negative test. Rejected — it would be
demonstration code wearing a security claim, which is the exact failure mode this
repository argues against.
