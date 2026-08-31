# CrewAI transitive dependency risk acceptance

Date recorded: 2026-08-31

## Context

CrewAI 1.15.18 declares `chromadb~=1.1.0` as a mandatory dependency. The current
CrewAI baseline in this repository uses `Agent`, `Task`, and `Crew` for structured
LLM reasoning only. It does not enable CrewAI memory or knowledge features and does
not start or expose a ChromaDB server.

The upstream ChromaDB line required by CrewAI currently has security advisories with
no patched release available inside the CrewAI-compatible version range.

## Accepted findings

The dependency audit is allowed to ignore only these vulnerability identifiers:

- `PYSEC-2026-311` / CVE-2026-45829 — pre-authentication ChromaDB server code injection
- `GHSA-2wm9-hf6c-p5cr` / CVE-2026-45830 — cross-tenant authorization failure
- `GHSA-xph7-9rjv-w5fr` / CVE-2026-45831 — authorization scope failure
- `GHSA-36p7-vc44-83pf` / CVE-2026-45833 — authenticated ChromaDB server code injection

No package-wide or severity-wide audit bypass is permitted. Any additional finding
continues to fail the dependency quality gate.

## Scope justification

The accepted findings target ChromaDB server APIs, authorization behavior, or server-side
model-loading paths. The current adapter does not instantiate ChromaDB, use CrewAI memory
or knowledge storage, or expose a ChromaDB network endpoint.

This is therefore a constrained acceptance of an unreachable transitive attack surface in
the current baseline, not an assertion that the affected ChromaDB release is safe.

## Removal conditions

Remove these exceptions as soon as any of the following becomes true:

1. CrewAI releases a version that no longer requires the affected ChromaDB range.
2. ChromaDB publishes a patched release compatible with CrewAI.
3. This project enables CrewAI memory, knowledge, RAG storage, or any ChromaDB-backed feature.
4. This project starts, embeds, or exposes a ChromaDB server or client against untrusted infrastructure.
5. New evidence shows the vulnerable code paths are reachable through the baseline CrewAI execution path.

Before adding CrewAI memory or knowledge features, this risk acceptance must be revisited
and the dependency audit must return to a no-exception posture for ChromaDB.
