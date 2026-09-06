# Development guide

This guide is the shortest path from a fresh clone to a safe change in the Agentic Security Framework Lab.

For architecture rationale, read [ARCHITECTURE.md](ARCHITECTURE.md). For repository-wide engineering rules, read [AGENTS.md](../AGENTS.md).

## Prerequisites

- Python 3.13
- [uv](https://docs.astral.sh/uv/)
- Git

The repository pins its Python line and dependency lock. Do not upgrade framework versions opportunistically inside an unrelated change.

## Setup

```bash
git clone https://github.com/brunovicco/agentic-security-framework-lab.git
cd agentic-security-framework-lab
uv sync --frozen --all-groups
```

Verify the full provider-free engineering gate:

```bash
uv run python scripts/quality_gate.py
```

The normal development and CI path does not require provider credentials.

## Discover focused checks

```bash
uv run python scripts/quality_gate.py --list
```

Use focused checks while iterating, but run the complete gate before proposing a merge.

The gate covers the repository's formatting/linting, strict typing, architecture/governance checks, tests, coverage, security scanning, and dependency audit. GitHub Actions additionally runs the MCP v2 compatibility / STDIO checks and the content-free OpenTelemetry observation check in isolated dependency contexts.

## Architecture in one minute

```text
Domain
  ↓
Application
  ↓
Ports / contracts
  ↓
Adapters
  ├── LangGraph
  ├── CrewAI
  ├── LlamaIndex
  ├── Agno
  └── gateway / transport integrations
```

The important dependency direction is inward.

Framework code may orchestrate the application, but framework-specific objects should not become the source of truth for domain policy, evidence identity, applicability, or final security decisions.

## Where changes normally belong

### `src/agentic_lab/domain/`

Use for framework-neutral business concepts, invariants, value semantics, and domain validation.

Do not import LangGraph, CrewAI, LlamaIndex, Agno, LiteLLM, MCP, or OpenTelemetry implementation SDKs here.

### `src/agentic_lab/application/`

Use for application use cases, evaluator/policy semantics, ports, and orchestration-independent contracts.

This layer owns the deterministic decisions that must stay stable across framework adapters.

### `src/agentic_lab/adapters/`

Use for framework-specific execution and external integration details.

Adapters may translate framework-native state/events/results into application contracts, but should not silently move business or security authority out of the Application layer.

### `scripts/`

Use for reproducible benchmarks, comparison runners, compatibility smokes, and quality tooling.

Provider-backed scripts should make model/gateway assumptions explicit and must not silently rewrite historical evidence.

### `artifacts/`

Treat accepted artifacts as immutable evidence.

Do not edit historical JSON/Markdown results to make them match later architecture changes. Generate a new artifact bundle for a new experiment.

### `docs/`

Update documentation when a change affects architecture, trust boundaries, framework behavior, methodology, privacy, or operational assumptions.

Record meaningful architectural decisions as ADRs. Do not create ADRs for trivial refactors.

## Safe change workflow

A typical small increment should look like:

```text
observed requirement / symptom
        ↓
identify owning layer
        ↓
add or update a focused regression test
        ↓
implement the smallest semantic change
        ↓
run focused checks
        ↓
run complete quality gate
        ↓
review docs/evidence impact
```

For debugging, prefer:

```text
Observed symptom
↓
Possible causes
↓
Evidence
↓
Root cause
↓
Fix
↓
Regression protection
```

Avoid changing several architecture boundaries in one PR unless they are inseparable.

## Adding or changing a framework adapter

Before changing framework behavior:

1. check the repository-pinned framework version;
2. read current official documentation and, when behavior is version-sensitive, the source for the pinned release;
3. identify which behavior belongs to the framework and which belongs to the application;
4. preserve the common domain-facing contract;
5. make retries/timeouts/telemetry behavior explicit when hidden defaults affect evidence or safety;
6. add provider-free contract tests where possible;
7. update the framework decision documentation if the trade-off changed materially.

Do not invent framework APIs from memory.

## Retry and timeout ownership

Retries can exist in several layers:

```text
application semantic retry
framework retry
SDK/client retry
gateway retry
provider retry
```

These are not equivalent.

The lab deliberately distinguishes application analysis attempts from actual model calls. Hidden client retries can distort that accounting and make failure behavior harder to govern.

When changing retry or timeout behavior, document the ownership boundary and add a regression test for the configured policy.

## Mutable execution failure ownership

For governed mutable actions, a raised executor exception is not equivalent to a clean non-execution. Once the executor boundary has been crossed, preserve the application-owned `GovernedActionExecutionError` / `ActionExecutionFailureEvidence` contract instead of converting it to a generic framework error.

Required invariants for this path:

- exactly one executor attempt unless a separate, explicitly designed retry/idempotency contract exists;
- `execution_attempted=true`;
- `failure_reason=executor_error`;
- `external_side_effect_state=unknown`;
- raw executor text remains outside structured evidence and governed error text;
- the original exception may remain only as the local Python `__cause__`;
- a claimed HITL approval is not silently restored after a failed executor attempt;
- framework status/error wrappers must not erase the application failure provenance.

At MCP boundaries, do not turn an uncertain post-executor governed failure into an ordinary model-correctable Tool error. The current local experiment maps only the typed governed failure class to a protocol `MCPError`; that transport behavior is not a substitute for idempotency or a host-level retry policy.

## Provider-backed development

Current framework clients reach providers through the LiteLLM gateway using the stable model-facing alias:

```text
security-analysis
```

Provider/model mapping belongs behind the gateway.

Do not reintroduce provider-native model names into framework adapters as a shortcut.

For local provider-backed experiments, follow:

- [LiteLLM gateway foundation](litellm/GATEWAY_FOUNDATION.md)
- [Final-evaluation methodology](evaluation/FINAL_EVALUATION.md)

Never commit API keys, gateway credentials, provider payloads, or copied trace URLs containing sensitive data.

## Telemetry and privacy

The project separates application-owned logical observations from provider/framework tracing.

Do not add prompts, responses, rationale, evidence text, feedback, credentials, provider payloads, or tool data to logical telemetry by default.

Read [PRIVACY.md](PRIVACY.md) before expanding telemetry attributes.

## MCP changes

MCP is an adapter/transport concern, not a Domain dependency.

When changing MCP behavior:

- preserve the application ports;
- keep authentication, trusted context, authorization, approval and approver authorization as separate concerns;
- preserve typed governed failure evidence and the `external_side_effect_state=unknown` contract after executor invocation;
- do not expose raw credentials or raw executor errors through Tool schemas/results/protocol data;
- preserve the distinction between model-visible Tool errors and host-visible protocol errors for uncertain mutable execution;
- run the MCP compatibility and real STDIO smoke gates;
- verify current MCP documentation/spec behavior before using new APIs.

Read [MCP.md](MCP.md) and the documents under [mcp/](mcp/).

## Evaluation and benchmark discipline

Comparisons are only useful when the contract stays stable.

For comparable framework runs, preserve:

- the same scenario dataset;
- the same repetition count;
- the same expected truth;
- the same governed model-facing alias;
- the same evaluation methodology;
- explicit retries/fallback metadata.

Do not tune prompts or controls solely to make one framework win a comparison.

Provider-backed final evaluation is intentionally not part of normal CI. Its accepted artifacts are tied to the exact evaluated Git commit.

## Before opening a PR

Run:

```bash
uv sync --frozen --all-groups
uv run python scripts/quality_gate.py
git diff --check
```

Then review:

- Is the change in the correct architectural layer?
- Did a framework abstraction accidentally take ownership of domain/security policy?
- Did a framework/transport error path erase authentication, authorization, approval or executor-failure provenance?
- Are retries, fallbacks, timeouts, mutable executor attempts, or model-call accounting still explicit?
- Did telemetry privacy change?
- Did provider/gateway ownership change?
- Did any historical artifact change unexpectedly?
- Does architecture/evaluation documentation need an update?

## Useful reading

- [Documentation map](README.md)
- [Architecture](ARCHITECTURE.md)
- [Framework decision matrix](FRAMEWORK_DECISION_MATRIX.md)
- [Executive overview](EXECUTIVE_OVERVIEW.md)
- [Final evaluation](evaluation/FINAL_EVALUATION.md)
- [Privacy](PRIVACY.md)
- [Engineering contract](../AGENTS.md)
