# LiteLLM milestone

Start with `GATEWAY_FOUNDATION.md` for the current architecture, documentation-freshness checkpoint, and the incremental framework client migrations.

Read `GATEWAY_SMOKE.md` for the first non-baseline LangGraph provider-backed compatibility smoke, its fail-closed acceptance criteria, artifact boundary, and manual review procedure.

Read `CREWAI_GATEWAY_SMOKE.md` for the CrewAI compatibility smoke that exercises both Agent/Task/Crew and Flow through the governed LiteLLM alias.

Read `LLAMAINDEX_GATEWAY_SMOKE.md` for the LlamaIndex Workflow compatibility smoke, including its async runtime path, fail-closed usage requirements, and evidence boundary.

Read `AGNO_GATEWAY_SMOKE.md` for the Agno Workflow schema-v2 compatibility smoke, including the separate transport-compatibility, semantic-quality, and system-safety evidence dimensions.

The accepted manual review of the first persisted LangGraph gateway smoke is recorded in `LANGGRAPH_GATEWAY_SMOKE_REVIEW.md`, with the machine-readable decision in `langgraph_gateway_smoke_review.json`.

The accepted manual review of the corrected persisted CrewAI gateway smoke is recorded in `CREWAI_GATEWAY_SMOKE_REVIEW.md`, with the machine-readable decision in `crewai_gateway_smoke_review.json`.

The accepted manual review of the persisted LlamaIndex schema-v2 gateway smoke is recorded in `LLAMAINDEX_GATEWAY_SMOKE_REVIEW.md`, with the machine-readable decision in `llamaindex_gateway_smoke_review.json`. The review preserves the earlier controlled `product-mismatch` semantic-variability finding instead of treating the accepted 5/5 run as proof of semantic determinism.

The accepted manual review of the persisted Agno schema-v2 gateway smoke is recorded in `AGNO_GATEWAY_SMOKE_REVIEW.md`, with the machine-readable decision in `agno_gateway_smoke_review.json`.

The architectural decision is recorded in `docs/adr/0002-centralize-llm-provider-access-behind-litellm-proxy.md`.
