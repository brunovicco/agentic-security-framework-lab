# Adversarial Security Evaluation v2 — Official Baseline Comparison

This report compares only accepted, like-for-like official baselines.

| Baseline | Task | Security | Model attack | Unsafe | Retry | Fallback | Mean latency | p50 | p95 | Mean tokens |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| langgraph | 100% | 100% | 0% | 0% | 0% | 0% | 2503.86 ms | 2493.62 ms | 3256.20 ms | 763.17 |
| crewai-flow | 100% | 100% | 0% | 0% | 0% | 0% | 2924.21 ms | 2734.80 ms | 5864.32 ms | 795.94 |
| llamaindex-workflow | 100% | 100% | 0% | 0% | 0% | 0% | 2769.70 ms | 2680.28 ms | 4135.12 ms | 793.11 |
| agno-workflow | 100% | 100% | 0% | 0% | 0% | 0% | 3085.49 ms | 2628.05 ms | 10151.05 ms | 791.22 |

## Interpretation

- No framework winner is declared from this sample.
- Latency and token differences are descriptive only; provider variance is material.
- The canonical suite observed no successful live model attack in these accepted runs, so containment-after-attack rates are not exercised here.
- Deterministic rejection and fallback containment remain evidenced by the separate LangGraph sensitivity control.
- The LangGraph baseline is a pinned legacy official artifact; newer baselines require explicit accepted-review promotion metadata.
