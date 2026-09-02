# LlamaIndex transitive dependency risk acceptance

Date recorded: 2026-09-02

## Context

`llama-index-core==0.14.24` installs `nltk==3.10.3` as a transitive dependency. The LlamaIndex baseline in this repository uses `Workflow` orchestration and structured prediction. It does not train, load, save, or parse NLTK model artifacts and does not use NLTK path security as an application containment boundary.

The current NLTK release has a [high-severity upstream advisory](https://github.com/nltk/nltk/security/advisories/GHSA-8mgp-746c-j5xp) with no patched release:

- `GHSA-8mgp-746c-j5xp` / CVE-2026-81726 — model-artifact APIs can bypass NLTK path security and access files outside configured roots.

The upstream advisory identifies these affected APIs:

- `TransitionParser.train`;
- `TransitionParser.parse`;
- `AveragedPerceptron.save`;
- `AveragedPerceptron.load`;
- `PerceptronTagger.save_to_json`;
- `save_maxent_params`.

The repository does not import NLTK or reference any of those APIs. NLTK is present only through `llama-index-core`.

## Accepted finding

The dependency audit may ignore only `GHSA-8mgp-746c-j5xp` for the currently locked NLTK transitive dependency.

No package-wide or severity-wide bypass is permitted. Any additional NLTK finding continues to fail the dependency quality gate.

## Scope justification

The advisory requires an application to rely on NLTK `pathsec` enforcement while allowing an untrusted workflow to choose a model import or export path. This lab does neither. Its LlamaIndex adapter sends in-memory vulnerability evidence to a structured LLM call and does not expose NLTK model-artifact operations or caller-controlled filesystem paths.

This is a constrained acceptance of an unreachable transitive attack surface, not an assertion that NLTK 3.10.3 is safe.

## Compensating constraints

- Do not import or call NLTK model-artifact APIs from application or adapter code.
- Do not accept caller-controlled model, tokenizer, tagger, parser, or export paths.
- Do not treat NLTK `pathsec` as a sandbox or authorization boundary.
- Keep the exception bound to the exact advisory identifier.
- Continue auditing the complete locked environment on every quality-gate run.

## Removal conditions

Remove the exception as soon as any of the following becomes true:

1. NLTK publishes a patched release compatible with `llama-index-core`.
2. LlamaIndex removes NLTK or narrows it to an unaffected release.
3. This project imports NLTK directly or uses any affected model-artifact API.
4. This project accepts untrusted paths for NLP model loading, persistence, parsing, or export.
5. New evidence shows an affected API is reachable through the current LlamaIndex workflow.

Before enabling any NLTK-backed model persistence or caller-selected filesystem path, this risk acceptance must be removed and the dependency audit must return to a no-exception posture for this advisory.
