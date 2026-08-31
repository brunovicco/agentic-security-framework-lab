# agentic-security-framework-lab

Framework-neutral Python 3.13 library using uv.
Governance profile: `none`.

```bash
uv lock --check
uv sync --frozen
uv run python scripts/quality_gate.py
```

The profile intentionally has no runtime framework, Dockerfile, structured-logging dependency, or
external tracing backend. See `AGENTS.md` for the engineering contract.
