# Agentic Security Framework Lab

[English](README.md) | [Português (Brasil)](README.pt-br.md)

[![quality](https://github.com/brunovicco/agentic-security-framework-lab/actions/workflows/quality.yml/badge.svg)](https://github.com/brunovicco/agentic-security-framework-lab/actions/workflows/quality.yml)

Um laboratório de engenharia framework-neutral para construir, proteger, avaliar e comparar **workflows de IA agêntica** sob os mesmos controles determinísticos.

O projeto implementa a mesma carga de análise de vulnerabilidades com **LangGraph, CrewAI, LlamaIndex e Agno**, centraliza acesso a providers com **LiteLLM**, valida o raciocínio do modelo fora do LLM, demonstra compatibilidade **MCP** e emite observações lógicas de **OpenTelemetry** sem conteúdo sensível.

> **Ideia central:** frameworks podem ser responsáveis pela orquestração, mas não devem automaticamente ser donos da autoridade de segurança, política, evidência ou decisão final.

## Por que este projeto importa

Frameworks agênticos tornam protótipos fáceis. Sistemas de IA mais próximos de produção precisam responder perguntas mais difíceis:

- O que acontece quando o modelo erra, mas o sistema ainda precisa produzir um resultado seguro?
- Quais controles devem permanecer determinísticos e independentes de framework?
- Como retries, fallback, tools, telemetria e acesso ao provider permanecem governáveis?
- Como comparar abstrações de orquestração mantendo carga, verdade esperada, alias de modelo e política de validação constantes?
- Como preservar evidência de *como* um resultado foi produzido, em vez de reportar apenas acurácia final?

Este repositório transforma essas perguntas em arquitetura executável, testes, evidências de benchmark e trade-offs explícitos.

## Leia o repositório de acordo com seu papel

| Público | Comece por | O que avaliar rapidamente |
| --- | --- | --- |
| **Developer / AI Engineer** | [Guia de desenvolvimento](docs/DEVELOPMENT.md) → [Arquitetura](docs/ARCHITECTURE.md) | boundaries, contratos tipados, adapters, retries, fallback, MCP, OTel, reprodutibilidade |
| **Engineering Manager / CIO / Arquiteto** | [Executive overview](docs/EXECUTIVE_OVERVIEW.md) → [Framework decision matrix](docs/FRAMEWORK_DECISION_MATRIX.md) | governança, fronteira de provider, trade-offs operacionais, portabilidade, disciplina de evidência |
| **Recrutador / Entrevistador** | este README → [Executive overview](docs/EXECUTIVE_OVERVIEW.md) | escopo, ownership de engenharia, tecnologias, avaliação mensurável, segurança e pensamento de plataforma |
| **Segurança / Governança** | [Arquitetura](docs/ARCHITECTURE.md) → [Evidências de segurança](docs/security/) | trust boundaries, controles determinísticos, testes adversariais, privacidade e telemetria |

Veja o [mapa completo da documentação](docs/README.md).

## O que o projeto demonstra

### Arquitetura e AI Engineering

- camadas de Domain e Application independentes de framework;
- adapters de frameworks abaixo de contratos estáveis da aplicação;
- structured output do LLM com validação determinística posterior;
- evaluator-optimizer com retry limitado;
- oracle fallback determinístico quando o reasoning probabilístico é rejeitado;
- separação entre tentativas de análise da aplicação e chamadas reais de modelo;
- acesso a modelo via alias governado e provider-neutral do LiteLLM;
- supressão de retries ocultos quando eles prejudicariam a qualidade da evidência;
- artifacts imutáveis de avaliação provider-backed vinculados a um commit Git exato.

### Segurança e governança

- o LLM raciocina sobre evidências, mas não é a fonte de verdade sensível à segurança;
- identidade da evidência e aplicabilidade são validadas fora do modelo;
- evidência não confiável não recebe autoridade de instrução por padrão;
- política determinística controla necessidade de revisão humana;
- telemetria proprietária de frameworks é desabilitada quando necessário para preservar a fronteira de privacidade;
- OpenTelemetry lógico contém somente metadata segura, sem prompts, respostas, rationale, evidência, credenciais ou payloads de provider;
- mapeamento provider/modelo permanece atrás do gateway em vez de vazar para cada adapter.

### Plataforma e interoperabilidade

- LangGraph evaluator-optimizer;
- CrewAI Agent / Task / Crew;
- CrewAI Flow com chamadas estruturadas diretas ao LLM;
- LlamaIndex Workflow com eventos tipados;
- Agno Workflow com primitives nativas de loop/condition;
- LiteLLM como fronteira centralizada de acesso a providers;
- compatibilidade MCP v2 mais smoke real local STDIO host/client;
- CI provider-free para qualidade, tipagem, segurança, MCP e contrato de OTel.

## Invariante central

```text
LLM raciocina
software valida
política restringe
runtime executa
evidência explica
```

O LLM é um componente probabilístico de raciocínio, não a autoridade final.

```text
                    ┌────────────────────────────┐
                    │  evidência determinística  │
                    └─────────────┬──────────────┘
                                  │
                                  ▼
                      análise probabilística
                                  │
                                  ▼
                    avaliador determinístico
                       │                    │
                     aceito              rejeitado
                       │                    │
                       │               retry limitado
                       │                    │
                       │             avaliação novamente
                       │                    │
                       │               esgotou?
                       │                    │
                       │                    ▼
                       │           oracle determinístico
                       └──────────────┬─────┘
                                      ▼
                            política determinística
                                      │
                                      ▼
                               AnalysisResult
```

Um resultado final correto **não significa necessariamente que o LLM acertou na primeira tentativa**. A distinção entre **qualidade do modelo** e **segurança do sistema** é uma das principais conclusões do laboratório.

## Snapshot da avaliação v1.0

A avaliação aceita da Phase 15 executa cinco variantes de orquestração sobre os mesmos cenários e pela mesma fronteira LiteLLM.

```text
Alias governado: security-analysis
Cenários: 5
Repetições por cenário: 3
Execuções por variante: 15
Execuções de framework: 75
Chamadas reais de modelo: 76
Commit avaliado: dd48c2490fc4ec1c76093577f7944d76a6fbc572
```

| Variante | Acurácia final esperada | Aceitação first-pass | Média de model calls | Latência média | Tokens médios |
| --- | ---: | ---: | ---: | ---: | ---: |
| LangGraph evaluator-optimizer | 100% | 100% | 1,00 | 3404,92 ms | **611,33** |
| CrewAI Agent + Task + Crew | 100% | 100% | 1,00 | 2987,15 ms | 1136,60 |
| CrewAI Flow + LLM estruturado direto | 100% | 100% | 1,00 | 3172,98 ms | 630,60 |
| LlamaIndex Workflow + `structured_predict()` | 100% | **93,33%** | **1,07** | 3214,98 ms | 732,20 |
| Agno Workflow + `Loop` / `Condition` nativos | 100% | 100% | 1,00 | **2980,14 ms** | 632,00 |

### O resultado mais importante não é escolher um vencedor

As cinco variantes alcançaram o resultado final esperado sob os mesmos controles da aplicação. A observação de engenharia mais útil é que **a abstração de orquestração mudou características de execução mesmo quando autoridade de segurança e fronteira de provider permaneceram compartilhadas**.

A comparação do CrewAI torna isso especialmente visível: Agent/Crew e Flow resolveram a mesma carga dentro do mesmo framework, mas produziram envelopes de tokens muito diferentes nesta amostra.

Também preservamos intencionalmente uma execução `product-mismatch` do LlamaIndex:

```text
tentativa 1 do LLM → rejeitada
tentativa 2 do LLM → rejeitada
oracle fallback determinístico → resultado final esperado
```

Essa execução explica por que 75 execuções de framework produziram **76 chamadas reais de modelo**. O laboratório preserva a anomalia porque evidência sobre recovery é mais útil do que um benchmark artificialmente uniforme.

### O que esses números não provam

- Não estabelecem significância estatística nem SLOs de produção.
- Quinze execuções por variante não sustentam rankings universais de latência.
- Os resultados não provam que um framework é geralmente superior.
- Os cenários adversariais são testes controlados, não prova de resistência ampla a prompt injection.
- O alias `security-analysis` é uma identidade governada do cliente, não atestado independente do modelo nativo selecionado atrás do gateway.

Evidência canônica:

- [Relatório five-way da Phase 15](artifacts/final-evaluation/phase15-20260905-v2/benchmarks/comparison/five-way-latest.md)
- [Comparação machine-readable](artifacts/final-evaluation/phase15-20260905-v2/benchmarks/comparison/five-way-latest.json)
- [Manifest da avaliação](artifacts/final-evaluation/phase15-20260905-v2/manifest.json)
- [Metodologia da avaliação final](docs/evaluation/FINAL_EVALUATION.md)

Artifacts provider-direct históricos permanecem imutáveis e não são reescritos para refletir hardening posterior de gateway ou runtime.

## Implementações por framework

| Framework / abstração | Orquestração nativa | Structured reasoning | Fronteira de provider | Autoridade determinística |
| --- | --- | --- | --- | --- |
| LangGraph | graph nodes + conditional routing | LangChain structured output | LiteLLM `security-analysis` | Application |
| CrewAI Agent/Crew | `Agent` + `Task` + `Crew` | structured CrewAI output | LiteLLM `security-analysis` | evaluator da Application |
| CrewAI Flow | Flow routing/state | `LLM.call()` estruturado direto | LiteLLM `security-analysis` | Application |
| LlamaIndex Workflow | eventos tipados de Workflow | `structured_predict()` | LiteLLM `security-analysis` | Application |
| Agno Workflow | `Workflow` + `Loop` + `Condition` | Agent structured output | LiteLLM `security-analysis` | Application |

Os frameworks são deliberadamente adapters, não donos das regras de negócio ou segurança. Consulte a [framework decision matrix](docs/FRAMEWORK_DECISION_MATRIX.md) para os trade-offs observados nesta carga.

## Fronteiras de confiança e provider

```text
Framework adapter
      │
      │ alias estável: security-analysis
      ▼
LiteLLM gateway
      │
      │ mapeamento de provider controlado pelo deployment
      ▼
LLM provider
```

Os clientes dos frameworks conhecem o alias estável e o contrato do gateway. Identificadores nativos e credenciais de provider permanecem fora do fluxo específico de cada framework.

Separadamente, a telemetria lógica da aplicação descreve fatos seguros da execução sem exportar automaticamente conteúdo do modelo:

```text
Execução da aplicação
      │
      ▼
AnalysisExecutionObservation
      │ apenas atributos allowlisted
      ▼
composição OpenTelemetry controlada pelo deployment
```

Leia [Arquitetura](docs/ARCHITECTURE.md), [LiteLLM gateway foundation](docs/litellm/GATEWAY_FOUNDATION.md) e [Privacy](docs/PRIVACY.md) para os detalhes.

## Quickstart para developers

Requisitos:

- Python 3.13
- [uv](https://docs.astral.sh/uv/)

```bash
git clone https://github.com/brunovicco/agentic-security-framework-lab.git
cd agentic-security-framework-lab
uv sync --frozen --all-groups
uv run python scripts/quality_gate.py
```

O quality gate normal é provider-free. Você **não precisa de API key de LLM** para validar contratos de engenharia, testes, tipagem, architecture checks, security checks ou comportamento determinístico.

Para checks focados:

```bash
uv run python scripts/quality_gate.py --list
```

Para experimentos provider-backed via LiteLLM, siga o [guia do gateway](docs/litellm/GATEWAY_FOUNDATION.md) e a [metodologia da avaliação final](docs/evaluation/FINAL_EVALUATION.md). A avaliação final provider-backed permanece deliberadamente fora do CI normal.

Leia o [guia completo de desenvolvimento](docs/DEVELOPMENT.md) antes de alterar adapters, evidência de avaliação, policy do gateway ou contratos de telemetria.

## Mapa do repositório

```text
src/agentic_lab/
├── domain/          # conceitos e invariantes independentes de framework
├── application/     # casos de uso, evaluator/policy, ports
└── adapters/        # LangGraph, CrewAI, LlamaIndex, Agno, gateway

config/litellm/      # configuração governada de acesso a provider
scripts/             # benchmarks, avaliação, quality gates e smokes
docs/                # arquitetura, ADRs, segurança, avaliação, MCP, privacy
artifacts/           # evidência imutável de benchmark/avaliação
tests/               # regressão e contratos provider-free
```

## Mapa da documentação

### Entender o projeto rapidamente

- [Documentação por audiência](docs/README.md)
- [Executive / portfolio overview](docs/EXECUTIVE_OVERVIEW.md)
- [Arquitetura e trust boundaries](docs/ARCHITECTURE.md)
- [Framework decision matrix](docs/FRAMEWORK_DECISION_MATRIX.md)

### Desenvolver e alterar o código

- [Guia de desenvolvimento](docs/DEVELOPMENT.md)
- [Engineering contract](AGENTS.md)
- [Agentic fast track](docs/AGENTIC_FAST_TRACK.md)

### Avaliar e reproduzir evidência

- [Metodologia da avaliação final](docs/evaluation/FINAL_EVALUATION.md)
- [Evidência five-way atual](artifacts/final-evaluation/phase15-20260905-v2/benchmarks/comparison/five-way-latest.md)
- [Manifest da avaliação](artifacts/final-evaluation/phase15-20260905-v2/manifest.json)

### Segurança, privacidade e interoperabilidade

- [Privacy boundary](docs/PRIVACY.md)
- [Experimentos de segurança](docs/security/)
- [MCP overview](docs/MCP.md)
- [LiteLLM gateway foundation](docs/litellm/GATEWAY_FOUNDATION.md)
- [Architecture decision records](docs/adr/)

## O que torna este projeto um portfólio de engenharia, e não apenas uma demo de framework

O repositório é construído ao redor de decisões que continuam válidas mesmo quando o framework é substituído:

1. **Domain e policy permanecem framework-neutral.**
2. **Saída probabilística é validada por software determinístico.**
3. **Falhas e recovery são observáveis em vez de ocultos.**
4. **Acesso ao provider é centralizado atrás de uma fronteira estável.**
5. **Telemetria possui contrato explícito de privacidade.**
6. **Evidência de benchmark é persistida e vinculada ao estado do código.**
7. **Trade-offs são documentados em vez de reduzidos a “framework X venceu”.**

Esses princípios são reutilizáveis ao discutir plataformas corporativas de agentes, AI gateways, runtimes governados, LLMOps, AI security ou seleção de frameworks.

## Status do projeto

O escopo de engenharia planejado para v1.0 está concluído: baseline de domínio, controles determinísticos, evolução de RAG, quatro famílias de frameworks / cinco variantes de orquestração, comparação de benchmark, LiteLLM, MCP, observabilidade, avaliação final, hardening de runtime e documentação de portfólio.

O repositório continua sendo um laboratório de engenharia, não uma afirmação de certificação para produção. Trabalhos futuros podem ampliar os experimentos sem reescrever a evidência histórica aceita.

Veja [CHANGELOG.md](CHANGELOG.md) para mudanças por release.
