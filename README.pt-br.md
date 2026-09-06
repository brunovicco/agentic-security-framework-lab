# Agentic Security Framework Lab

[English](README.md) | [Português (Brasil)](README.pt-br.md)

[![quality](https://github.com/brunovicco/agentic-security-framework-lab/actions/workflows/quality.yml/badge.svg)](https://github.com/brunovicco/agentic-security-framework-lab/actions/workflows/quality.yml)

Um laboratório de engenharia neutro em relação a frameworks para construir, proteger, avaliar e comparar **sistemas de IA agentic** sob os mesmos controles determinísticos.

O projeto implementa a mesma carga de análise de vulnerabilidades com **LangGraph, CrewAI, LlamaIndex e Agno**, centraliza o acesso a provedores com **LiteLLM**, valida raciocínio fora do LLM, testa compatibilidade com **MCP**, emite observações seguras de **OpenTelemetry** e exercita **ações mutáveis governadas** com autenticação, autorização source-aware, Human-in-the-Loop, autorização do aprovador e evidência tipada de execução/falha.

> **Ideia central:** frameworks podem ser responsáveis pela orquestração, mas não devem automaticamente ser donos da autoridade de segurança, política, autorização ou decisão final.

## Por que este projeto?

Frameworks agentic tornam protótipos fáceis. Sistemas mais próximos de produção precisam responder perguntas mais difíceis:

- quais controles devem permanecer determinísticos e independentes de framework?
- como comparar frameworks mantendo carga, verdade esperada e política constantes?
- como permitir que um agente proponha uma ação sem permitir que ele autorize a si próprio?
- como preservar evidência sobre *como* um resultado foi produzido?
- como separar identidade, autorização, aprovação humana e execução?
- o que fazer quando um executor mutável falha depois de já ter sido chamado?

Este repositório transforma essas perguntas em arquitetura executável, testes, benchmarks e trade-offs explícitos.

## Invariante central

```text
o LLM raciocina
o software valida
a política restringe
o runtime executa
a evidência explica
```

Para ações mutáveis:

```text
o agente/modelo propõe
composição confiável ou autenticação estabelece o contexto do chamador
a política autoriza
a aprovação humana é validada quando exigida
a política de aprovador valida a autoridade do revisor
o runtime executa
a evidência registra sucesso ou falha governada
```

E uma distinção permanece explícita:

```text
disponibilidade da ferramenta != autorização da ferramenta != execução da ferramenta
```

Veja [Governed Agent Actions](docs/security/GOVERNED_AGENT_ACTIONS.md) para o trust model completo.

## O que o projeto demonstra

### Arquitetura e AI Engineering

- Domain e Application independentes de framework;
- adapters de LangGraph, CrewAI, LlamaIndex e Agno abaixo de contratos estáveis;
- structured output com pós-validação determinística;
- evaluator-optimizer com retry limitado e fallback determinístico por oráculo;
- LiteLLM como fronteira provider-neutral;
- separação entre tentativas da aplicação e chamadas reais ao modelo;
- avaliação reproduzível com artifacts imutáveis vinculados a commits exatos.

### Segurança e governança

- `ProposedAction` é dado não confiável; `ActionContext` confiável vem de fora da entrada do modelo;
- autenticação e autorização são decisões separadas;
- autorização de menor privilégio usa o escopo exato `(caller_id, identity_source, action, resource, environment)`;
- escopos desconhecidos falham fechado;
- approval é limitada, single-use, revogável antes do claim e vinculada ao escopo exato no provider controlado single-process;
- a autoridade do aprovador é verificada separadamente;
- exceções pós-executor produzem failure evidence com `execution_attempted=true` e `external_side_effect_state=unknown`;
- credenciais brutas e texto bruto do executor não são copiados para a evidência estruturada;
- OpenTelemetry exporta apenas metadados seguros, não prompts, respostas, rationale, evidência ou credenciais.

### Plataforma e interoperabilidade

- LangGraph `StateGraph` e evaluator-optimizer;
- CrewAI Agent/Task/Crew e CrewAI Flow;
- LlamaIndex Workflow;
- Agno Workflow com `max_retries=0` para a ação mutável governada;
- MCP v2 com smokes locais STDIO para leitura, ação governada e experimento autenticado;
- conformance cross-framework comparando comportamento com a execução direta da Application;
- CI sem provedor para qualidade, tipagem, segurança, MCP e OTel.

## Prompt injection: posição do projeto

O projeto **não afirma impedir ou detectar prompt injection**. Ele assume que uma injection pode influenciar o raciocínio do modelo e pergunta: *que autoridade isso concede ao atacante?*

Em ações mutáveis, a resposta é: uma injection pode influenciar o `ProposedAction`, mas não cria por si só identidade, autorização, aprovação humana ou autoridade de aprovador.

Isso não significa que toda proposta maliciosa será bloqueada. Se ela já estiver dentro da autoridade legitimamente concedida ao caller e satisfizer todos os controles exigidos, ainda pode executar. Por isso, least privilege, escopo exato e desenho seguro de ferramentas continuam essenciais.

Os cenários adversariais do repositório exercitam pontos específicos dessa fronteira; não são prova de resistência ampla a prompt injection.

## Runtime governado atual

O último release publicado é **v1.3.0 — Human Approval Lifecycle**. A `main` atual preserva os contratos de v1.1/v1.2/v1.3 e inclui hardening posterior para autorização de aprovador, failure provenance, uncertain execution em MCP, preservação de erro no Agno e conformance cross-framework de falha.

A fronteira atual inclui:

- `ProposedAction(action, resource, environment)` como proposta não confiável;
- `ActionContext(caller_id, identity_source)` confiável e separado;
- outcomes `allow`, `deny` e `require_human_approval`;
- `HumanApprovalEvidence` com validade temporal e claim single-use no provider single-process;
- approver authorization para `(approver_id, caller_id, identity_source, action, resource, environment)`;
- autenticação de service caller antes da autorização source-aware;
- `GovernedActionRuntime` como ponto único de enforcement antes da execução;
- `ActionExecutionEvidence`, `ActionExecutionFailureEvidence` e variantes autenticadas;
- adapters governados para LangGraph, CrewAI Flow, LlamaIndex Workflow e Agno Workflow;
- tratamento MCP de execução incerta como erro de protocolo visível ao host, não como Tool error normal corrigível pelo modelo;
- exatamente uma tentativa de executor no cenário controlado de falha usado na matriz de conformance.

Isso é **evidência provider-free de integração Application/framework/MCP**. Não é uma alegação de IAM production-grade, identidade remota OAuth/OIDC/JWT/mTLS, approval distribuído, idempotência, rollback/compensation, PDP externo, evidência tamper-proof ou certificação de produção.

## Fronteiras arquiteturais declaradas

Os limites atuais são documentados explicitamente em ADRs:

- [ADR 0009 — Tamper-evident execution evidence](docs/adr/0009-tamper-evident-execution-evidence.md): a evidência atual preserva provenance em memória, mas não prova que um registro não foi alterado depois de produzido.
- [ADR 0010 — Approval authority is single-process](docs/adr/0010-approval-authority-is-single-process.md): single-use, revogação e validade temporal são garantias do provider controlado dentro de um único processo.
- [ADR 0011 — Uncertain external side effects](docs/adr/0011-uncertain-external-side-effects-idempotency-and-reconciliation.md): `external_side_effect_state=unknown` permanece terminal no lab; idempotency/reconciliation ficam para um executor externo real.
- [ADR 0012 — External PDP boundary](docs/adr/0012-exact-scope-authorization-and-external-pdp-boundary.md): o authorizer exato e in-process permanece como referência; um PDP futuro deve preservar a mesma semântica de autoridade.

Esses ADRs documentam **limites e critérios de evolução**, não funcionalidades já implementadas.

## Avaliação v1.0

A Phase 15 comparou cinco variantes de orquestração nos mesmos cinco cenários e pela mesma fronteira LiteLLM:

```text
Cenários: 5
Repetições por cenário: 3
Execuções por variante: 15
Execuções de framework: 75
Chamadas reais ao modelo: 76
Commit avaliado: dd48c2490fc4ec1c76093577f7944d76a6fbc572
```

| Variante | Tokens médios | Latência média | Chamadas médias ao modelo | Aceitação first-pass | Resultado esperado |
| --- | ---: | ---: | ---: | ---: | ---: |
| LangGraph evaluator-optimizer | **611,33** | 3404,92 ms | 1,00 | 100% | 100% |
| CrewAI Agent + Task + Crew | 1136,60 | 2987,15 ms | 1,00 | 100% | 100% |
| CrewAI Flow + LLM estruturado direto | 630,60 | 3172,98 ms | 1,00 | 100% | 100% |
| LlamaIndex Workflow + `structured_predict()` | 732,20 | 3214,98 ms | **1,07** | **93,33%** | 100% |
| Agno Workflow + `Loop`/`Condition` | 632,00 | **2980,14 ms** | 1,00 | 100% | 100% |

Todas chegaram ao resultado final esperado. O principal achado não é “qual framework venceu”, mas que **o caminho de execução e o custo mudaram mesmo mantendo autoridade e políticas da aplicação constantes**.

A execução `product-mismatch` do LlamaIndex precisou de duas tentativas rejeitadas antes do fallback determinístico, explicando por que 75 execuções produziram 76 chamadas reais ao modelo.

Esses números não estabelecem significância estatística, SLOs de produção ou superioridade universal de um framework.

Evidência canônica:

- [Relatório five-way da Phase 15](artifacts/final-evaluation/phase15-20260905-v2/benchmarks/comparison/five-way-latest.md)
- [Manifesto da avaliação](artifacts/final-evaluation/phase15-20260905-v2/manifest.json)
- [Metodologia da avaliação final](docs/evaluation/FINAL_EVALUATION.md)

## Frameworks e autoridade

| Framework | Orquestração | Dono da autorização/enforcement |
| --- | --- | --- |
| LangGraph | graph / `StateGraph` | `GovernedActionRuntime` |
| CrewAI | Agent/Crew e Flow | `GovernedActionRuntime` |
| LlamaIndex | Workflow | `GovernedActionRuntime` |
| Agno | Workflow / Step | `GovernedActionRuntime` |

Os frameworks são adapters. A Application continua dona das regras de autorização, approval e enforcement.

## MCP

O projeto separa três superfícies locais:

```text
agentic-security-applicability                  # leitura/análise
agentic-security-governed-actions               # ação mutável por trusted composition
agentic-security-authenticated-governed-actions # experimento autenticado isolado
```

Nos fluxos mutáveis, `resource` e `environment` são inputs não confiáveis; identidade, approval e approver não vêm do schema da Tool. Falhas pós-executor com side effect incerto são convertidas em `MCPError` para o host, sem afirmar que o efeito externo não aconteceu.

Veja [MCP](docs/MCP.md) para os detalhes.

## Início rápido

Requisitos: Python 3.13 e [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/brunovicco/agentic-security-framework-lab.git
cd agentic-security-framework-lab
uv sync --frozen --all-groups
uv run python scripts/quality_gate.py
```

O quality gate padrão roda sem chave de LLM.

## Documentação

- [Visão executiva](docs/EXECUTIVE_OVERVIEW.md)
- [Arquitetura](docs/ARCHITECTURE.md)
- [Governed Agent Actions](docs/security/GOVERNED_AGENT_ACTIONS.md)
- [MCP](docs/MCP.md)
- [Matriz de decisão de frameworks](docs/FRAMEWORK_DECISION_MATRIX.md)
- [Guia de desenvolvimento](docs/DEVELOPMENT.md)
- [ADRs](docs/adr)
- [Mapa completo da documentação](docs/README.md)

## Status

O escopo planejado da **v1.0** está completo. Os releases publicados pós-v1.0 são **v1.1 Governed Agent Actions**, **v1.2 Trusted Caller Identity** e **v1.3 Human Approval Lifecycle**.

A `main` atual inclui hardening posterior de autorização, evidence e integração MCP/framework sem reescrever artifacts históricos ou releases publicados.

Este continua sendo um **laboratório de engenharia**, não uma alegação de certificação de produção.

Veja o [CHANGELOG.md](CHANGELOG.md) para mudanças em nível de release.
