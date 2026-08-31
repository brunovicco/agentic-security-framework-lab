# ADR-0001: Separate Deterministic Evidence from Agentic Reasoning

## Status

Accepted

## Date

2026-08-30

## Context

Agentic Security Framework Lab compares multiple agentic frameworks by implementing the same vulnerability-analysis workload with shared domain concepts, contracts, tools, datasets, policies, evaluation scenarios, and metrics.

The project must be able to distinguish facts obtained from authoritative or deterministic sources from assessments produced through probabilistic reasoning.

Vulnerability intelligence can include observations such as CVE metadata, CVSS measurements, EPSS scores, CISA KEV status, affected package ranges, asset inventory records, deployed versions, and exposure attributes. These facts should remain independently verifiable and reproducible.

Agentic systems can provide value when correlating evidence, reasoning about context, explaining material risk, identifying uncertainty, and producing recommendations. However, allowing an LLM or orchestration framework to establish authoritative evidence would make results harder to reproduce, audit, compare, and debug.

The project also needs to compare different agentic frameworks fairly. If each framework retrieves, represents, or establishes different underlying facts, benchmark results would compare different workloads rather than different orchestration approaches.

OpsLens is an existing project that builds deterministic vulnerability-intelligence evidence from sources such as NVD, FIRST EPSS, CISA KEV, and GHSA. Its evidence and provenance concepts are useful references for this lab, but its AWS runtime, source-specific models, ingestion architecture, and persistence concerns should not become dependencies of the Agentic Security Framework Lab domain.

## Decision

The project will maintain an explicit architectural boundary between deterministic evidence and agentic reasoning.

Deterministic evidence represents observations that can be independently obtained, validated, and reproduced without relying on an LLM's judgment.

Agentic reasoning consumes validated evidence and may correlate, synthesize, explain, or reason about that evidence, but it does not redefine observed facts as authoritative evidence.

The conceptual flow is:

```text
External or local data sources
        |
        v
Deterministic acquisition
        |
        v
Validation and normalization
        |
        v
Observed evidence
        |
        +---------------------------+
        |                           |
        v                           v
Deterministic baseline         Agentic reasoning
        |                           |
        |                           v
        |                    Derived assessment
        |                           |
        +-------------+-------------+
                      |
                      v
             Deterministic policy
                      |
                      v
              Recommended action
```

The project will conceptually distinguish at least four categories:

```text
Observed fact
Derived assessment
Policy decision
Execution action
```

An observed fact is evidence obtained from a source or deterministic process.

A derived assessment is an interpretation or conclusion produced from one or more observations.

A policy decision is the result of explicit project rules or authorization logic.

An execution action is a mutation or external side effect performed by the runtime.

These categories must not be silently collapsed into a single generic evidence structure.

### Relationship with OpsLens

OpsLens is treated as an evidence producer and architectural reference, not as the owner of this project's domain.

Agentic Security Framework Lab will define source-neutral contracts for the evidence required by its vulnerability-analysis workload.

The lab must not directly depend on OpsLens source-specific domain models or AWS runtime components.

Initial phases will use local deterministic repositories and fixtures.

A later integration may consume exported deterministic OpsLens evidence through a stable adapter or fixture format without requiring agentic framework implementations to know that OpsLens produced it.

The desired relationship is:

```text
OpsLens
NVD / EPSS / KEV / GHSA
        |
        v
deterministic evidence export
        |
        v
source-neutral evidence adapter
        |
        v
Agentic Security Framework Lab
        |
        +--> deterministic reference implementation
        |
        +--> LangGraph adapter
        |
        +--> LlamaIndex adapter
        |
        +--> CrewAI adapter
        |
        +--> Agno adapter
```

All framework implementations must consume equivalent evidence for common benchmark scenarios.

### Authority rule

When deterministic evidence and generated reasoning disagree, the deterministic evidence remains authoritative for the observed fact.

An agent may report uncertainty, conflict, missing evidence, or inability to reach a conclusion.

It must not silently modify an observed fact to make its reasoning internally consistent.

## Alternatives considered

### Allow each agentic framework to own evidence retrieval and representation

Under this approach, each framework implementation could independently retrieve vulnerability information and construct its own internal representation.

This was rejected because differences in retrieval, source selection, parsing, and representation would contaminate framework benchmarks. The project could no longer determine whether a result difference came from orchestration quality or different underlying evidence.

### Directly reuse OpsLens domain models

Under this approach, Agentic Security Framework Lab would import source-specific models from OpsLens.

This was rejected because OpsLens models represent concerns such as source observations, ingestion provenance, content versioning, and source-specific normalization that do not necessarily belong in the agentic lab's source-neutral domain.

It would also create unnecessary coupling between projects that have different responsibilities and development lifecycles.

Concepts and fixture data may be reused without sharing domain ownership.

### Reimplement vulnerability-source ingestion inside this repository

Under this approach, the lab would independently implement NVD, EPSS, CISA KEV, GHSA, and other ingestion pipelines.

This was rejected for the initial architecture because it duplicates OpsLens responsibilities and distracts from the primary learning objective: agentic orchestration and framework comparison.

Source integrations may be introduced later only when required by a specific experiment.

### Allow LLM output to become evidence after generation

Under this approach, generated facts could be promoted directly into the evidence set.

This was rejected because model output is probabilistic and may contain unsupported inference or hallucination.

Generated claims may become assessments or hypotheses, but they require independent validation before being represented as observed evidence.

## Consequences

### Positive

* Framework comparisons can use identical evidence.
* Deterministic scenarios can act as reference or oracle behavior for evaluation.
* Evidence provenance remains auditable.
* Agent hallucinations cannot silently rewrite authoritative observations.
* OpsLens can contribute evidence without coupling the two projects.
* Failure analysis becomes easier because evidence acquisition and reasoning are separate stages.
* Future framework adapters remain focused on orchestration rather than domain ownership.

### Negative

* The project needs explicit contracts between evidence acquisition and reasoning.
* Some data structures may appear more verbose because observations, assessments, policies, and actions remain distinct.
* Framework-native data structures may require translation into project-owned contracts.
* End-to-end demos may initially appear less autonomous because deterministic components retain authority over facts and policy.

These tradeoffs are intentional.

## Security and privacy impact

Treating model output as non-authoritative reduces the risk that hallucinated or manipulated content becomes trusted system state.

External source content, retrieved documents, tool output, MCP responses, and model output remain untrusted until validated according to their boundary.

Prompt injection or malicious retrieved content must not be able to overwrite authoritative vulnerability evidence or deterministic policy rules merely through generated text.

No sensitive or private production data is required by this decision.

Fixtures used for evaluation should use public, synthetic, or appropriately sanitized data.

## Operational impact

No external service or runtime dependency is introduced by this decision.

Initial implementations should use local deterministic repositories and static fixtures.

The project does not require OpsLens, AWS, Athena, S3, Glue, or external vulnerability APIs to execute its first vertical slice.

This keeps early tests fast, reproducible, and suitable for CI.

Future OpsLens integration, if introduced, must be implemented behind a project-owned adapter and must preserve the same source-neutral contract consumed by local fixtures.

## Follow-up

1. Define source-neutral domain concepts for vulnerability identity, assets, observations/evidence, assessments, policy decisions, and actions.
2. Avoid freezing one large `VulnerabilityAnalysis` model before those responsibilities are understood.
3. Build the first deterministic vulnerability-analysis vertical slice using local fake repositories.
4. Use that deterministic slice as reference behavior for later agentic implementations.
5. Introduce framework adapters only after shared application contracts exist.
6. Define a stable evidence-fixture format before integrating real OpsLens exports.
7. Revisit direct runtime integration with OpsLens only if static exported evidence becomes insufficient for a concrete experiment.
