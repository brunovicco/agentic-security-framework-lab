# ADR 0012: Exact-scope authorization and the external PDP boundary

- **Status:** Accepted — exact in-process authorization retained; external PDP deferred
- **Date:** 2026-09-06
- **Scope:** action authorization, `GovernedActionRuntime`
- **Related:** `docs/ARCHITECTURE.md` §3, §7, §17

## Context

Current authorization evaluates an exact, source-aware tuple:

```
(caller_id, identity_source, action, resource, environment)
```

There are no wildcards, no hierarchical scopes, no nearest-match, and no
cross-source fallback. Any unknown component has no matching rule and fails closed.

This is a deliberate phase-1 choice, and the reason is worth stating precisely: it
removes the policy engine from the trust argument. When matching is exact, the claim
*"an unauthorized caller cannot reach the executor"* is verifiable by inspection.
The moment wildcards, precedence rules, or scope hierarchies exist, that claim
becomes a claim about the matching algorithm, and the adversarial tests would be
testing the engine rather than the architecture.

The cost is equally clear. The policy set grows as

```
|callers| × |identity_sources| × |actions| × |resources| × |environments|
```

which is fine for a controlled lab matrix and untenable for any real domain. A
reasonable reviewer will ask whether the model survives contact with a policy set
that cannot be enumerated by hand.

## Decision

Retain the exact in-process authorizer as the reference implementation. Do not
adopt Cedar, OPA, or any external policy engine in the current scope. Record the
migration shape and the acceptance criterion so the limitation is a bounded
phase-1 choice rather than an unexamined one.

## Migration shape

The port already exists. Authorization sits behind an application-owned contract,
and the runtime depends on that contract rather than on the matcher. Substituting
the decision engine is therefore the same replaceability test this repository
already applies to orchestration frameworks:

> If the policy engine is replaced, does the authority model still hold?

**Mapping.** The current tuple maps onto a standard PDP request without loss:

| Current component | PDP request |
| --- | --- |
| `caller_id` + `identity_source` | principal (composite; the source is part of principal identity, not an attribute) |
| `action` | action |
| `resource` | resource |
| `environment` | context |

Keeping `identity_source` inside the principal rather than as a context attribute
is the non-obvious part. Demoting it to an attribute is exactly how the current
no-cross-source-inheritance property would be silently lost.

**Topology.** `GovernedActionRuntime` becomes the PEP. The PDP is either an
embedded evaluator (Cedar as a library) or an out-of-process sidecar (OPA). The
enforcement point does not move; only the decision does.

**Concerns introduced by the change** — and the actual reason this is a separate
experiment rather than a refactor:

- *Decision caching and staleness.* A cached `allow` outlives a policy change. Any
  cache needs an explicit staleness bound recorded in evidence.
- *Policy versioning.* A decision is only interpretable alongside the policy that
  produced it. `ActionExecutionEvidence` would need a `policy_version` fact, which
  is a contract change, not a configuration change.
- *Availability.* PDP unreachable must mean deny. This trades availability for
  safety deliberately and must be tested, not assumed.
- *Scope hierarchy.* Wildcards reintroduce the near-match class of errors that
  exactness eliminated. If hierarchical scopes are adopted, the adversarial suite
  needs cases specifically targeting precedence and shadowing.

**Acceptance criterion.** The existing cross-framework conformance matrix is reused
unchanged. The external PDP is accepted only if every scenario — exact allow,
explicit deny, caller mismatch, identity-source mismatch, resource escalation,
unauthorized approver — produces outcomes identical to the in-process baseline.
Behavioural equivalence, not API compatibility, is the bar. That is the same
standard already applied to framework adapters.

## Consequences

- The non-goal *"RBAC/ABAC policy languages, wildcard/hierarchical action scopes"*
  stands, but now with a stated path and a defined acceptance test.
- The current authorizer remains the semantic reference. If an external PDP ever
  disagrees with it on the conformance matrix, the PDP configuration is wrong.
- Evidence contracts are known to require one additive change (`policy_version`)
  before this migration, which is now recorded rather than discovered later.

## Revisit triggers

- The policy set stops being enumerable by hand in a test fixture.
- An experiment needs policy authored or reviewed by someone who is not the
  application developer.
- Multiple applications need to share one policy set.

## Alternatives considered

**Add wildcards to the in-process matcher.** Cheapest option, and it quietly
converts the strongest property of the current design into a property of a
hand-written matcher with no independent test suite. Rejected.

**Adopt OPA now.** Introduces distribution, caching, and versioning concerns before
there is a policy set large enough to justify any of them. The experiment would
demonstrate integration, not governance. Rejected as premature.
