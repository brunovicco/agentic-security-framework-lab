# ADR 0010: Approval authority is single-process

- **Status:** Accepted — single-process enforcement is the declared boundary
- **Date:** 2026-09-06
- **Scope:** `HumanApprovalEvidence`, `ActionApprovalProvider`, `ActionApproverAuthorizer`
- **Related:** `docs/ARCHITECTURE.md` §7, `docs/security/GOVERNED_AGENT_ACTIONS.md`

## Context

The approval model treats human approval as bounded authority rather than a
boolean. Approval evidence is exact-scope, timezone-aware, single-use, revocable
before claim, source-isolated, evaluated against an application-owned trusted
clock, and subject to independent approver authorization for the exact
`(approver_id, caller_id, identity_source, action, resource, environment)` scope.

Every one of those properties is straightforward to enforce correctly in a single
process with in-memory state, and every one of them becomes a distributed systems
problem with more than one replica. The current implementation is correct. It is
correct for a reason that does not survive horizontal scaling, and that reason
should be written down rather than left for a reader to discover.

Naming this precisely also matters for how the project is read: single-use
approval is the property most likely to be assumed portable by someone skimming
the trust model.

## Decision

Single-process enforcement remains the boundary. Durable and distributed approval
stay non-goals. This ADR records the specific failure modes that a naive
distribution would introduce, and the acceptance criterion any future experiment
must meet.

## Failure modes under naive distribution

**Claim race.** Two replicas read the same unclaimed approval, both validate it,
both proceed. Single-use becomes double-use, and the mutable action executes twice
under one human authorization. Correct handling requires the claim to be an atomic
compare-and-set at the store — conditional write, or `SELECT ... FOR UPDATE` — not
a read-then-write in application code. This is the most dangerous of the four,
because both executions produce individually well-formed evidence and nothing in
either record reveals the race.

**Revocation staleness.** A replica caches approval state; revocation lands between
the cached read and the claim. Revocation-before-claim, as a guarantee, requires
that revocation status be evaluated inside the same atomic operation as the claim.
The practical consequence is that approval state cannot be cached at all — the
claim is the read.

**Clock divergence.** The application-owned trusted clock is a single clock today.
Across replicas, validity windows evaluated against local time admit both premature
and expired claims within the skew envelope. Either the store evaluates the window,
or the maximum tolerated skew becomes an explicit, documented security parameter
with an enforced NTP assumption. Silently trusting replica-local time is the
failure that will not show up in testing.

**Partition behaviour.** An unreachable approval store must block execution. This
is a deliberate availability sacrifice and should be tested as a positive
requirement rather than encountered as an outage.

## Acceptance criterion for a future experiment

A distributed approval experiment is accepted only if it demonstrates:

- exactly one successful execution under *N* concurrent claims of the same
  single-use approval, with the other *N-1* producing typed rejection evidence;
- revocation landing concurrently with a claim resolving deterministically to
  exactly one of claimed-or-revoked, never both, never neither;
- validity-window evaluation independent of replica-local clocks;
- fail-closed behaviour with the approval store unreachable;
- the existing conformance matrix passing unchanged against the distributed
  provider.

Concurrency here is the test, not a footnote to it. An experiment that only
demonstrates durable storage of approvals has demonstrated persistence, not
approval authority.

## Consequences

- The current in-memory provider stays the semantic reference for what approval
  authority *means*; distribution would change where it is enforced, not what it
  guarantees.
- The trust model documentation should state single-process enforcement explicitly,
  so that single-use is not read as a portable guarantee.
- Any future durable provider inherits a defined acceptance bar rather than an
  implicit one.

## Revisit triggers

- More than one enforcement replica.
- Approval that must survive process restart.
- An approval surface reachable by a reviewer outside the enforcing process.

## Alternatives considered

**Durable store, no atomic claim.** Buys persistence and loses single-use, which is
the property that makes bounded approval meaningful. Strictly worse than the
current in-memory model despite looking more production-shaped. Rejected.

**Distributed lock around the claim.** Workable, and it adds lock lifetime, lease
expiry, and fencing-token concerns that are their own security surface — a lock
expiring mid-claim reintroduces the race it was added to prevent. Not rejected on
merit; rejected as out of scope until a concrete experiment requires it.
