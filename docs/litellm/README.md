# LiteLLM milestone

Start with `GATEWAY_FOUNDATION.md` for the current architecture, documentation-freshness checkpoint, and the incremental framework client migrations.

Read `GATEWAY_SMOKE.md` for the first non-baseline LangGraph provider-backed compatibility smoke, its fail-closed acceptance criteria, artifact boundary, and manual review procedure.

Read `CREWAI_GATEWAY_SMOKE.md` for the CrewAI compatibility smoke that exercises both Agent/Task/Crew and Flow through the governed LiteLLM alias.

The accepted manual review of the first persisted LangGraph gateway smoke is recorded in `LANGGRAPH_GATEWAY_SMOKE_REVIEW.md`, with the machine-readable decision in `langgraph_gateway_smoke_review.json`.

The architectural decision is recorded in `docs/adr/0002-centralize-llm-provider-access-behind-litellm-proxy.md`.
