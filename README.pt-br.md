# Agentic Security Framework Lab

[![quality](https://github.com/brunovicco/agentic-security-framework-lab/actions/workflows/quality.yml/badge.svg)](https://github.com/brunovicco/agentic-security-framework-lab/actions/workflows/quality.yml)

Um laboratório controlado de engenharia para comparar **LangGraph, CrewAI, LlamaIndex e Agno** usando a mesma carga de trabalho sensível à segurança.

O projeto busca responder a uma pergunta prática e deliberadamente restrita:

> O que muda quando diferentes abstrações de orquestração agêntica resolvem o mesmo problema sob as mesmas evidências, verdade esperada, validação determinística, retry, fallback, política e fronteira governada de modelo?

A carga de trabalho é análise de aplicabilidade de vulnerabilidades. O LLM pode raciocinar sobre a evidência, mas nunca é a autoridade final sobre decisões sensíveis de segurança.

## Invariante central

```text
LLM raciocina
software valida
política restringe
runtime executa
evidência explica
```

O LLM é tratado como um componente probabilístico de raciocínio.

O software determinístico da aplicação continua responsável por:

- validar a identidade da evidência;
- validar aplicabilidade;
- decidir se um retry é permitido;
- executar fallback determinístico;
- aplicar a política de revisão humana;
- construir o `AnalysisResult` final.

## Avaliação final five-way atual

A avaliação do estado atual executa as cinco variantes de orquestração pela mesma fronteira centralizada do gateway LiteLLM.

```text
Alias governado do cliente: security-analysis
Cenários: 5
Repetições por cenário: 3
Execuções por variante: 15
Execuções de framework: 75
Chamadas de modelo: 76
Sampling: provider default
Commit avaliado: dd48c2490fc4ec1c76093577f7944d76a6fbc572
```

O alias `security-analysis` é a identidade governada solicitada por todos os clientes de framework. Ele é deliberadamente diferente de um identificador nativo do provider: o mapeamento provider/modelo pertence ao gateway LiteLLM.

| Variante | Acurácia esperada | First pass | Média de calls | Latência média | p50 | Tokens médios |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| LangGraph evaluator-optimizer | 100% | 100% | 1,00 | 3404,92 ms | 3447,83 ms | **611,33** |
| CrewAI Agent + Task + Crew | 100% | 100% | 1,00 | 2987,15 ms | 3049,42 ms | 1136,60 |
| CrewAI Flow + LLM estruturado direto | 100% | 100% | 1,00 | 3172,98 ms | 3082,20 ms | 630,60 |
| LlamaIndex Workflow + `structured_predict()` | 100% | **93,33%** | **1,07** | 3214,98 ms | **2727,60 ms** | 732,20 |
| Agno Workflow + `Loop` / `Condition` | 100% | 100% | 1,00 | **2980,14 ms** | 3015,20 ms | 632,00 |

### O que a avaliação final mostra

As cinco variantes chegaram a **100% de acurácia esperada final** sob os mesmos controles da aplicação.

Uma execução `product-mismatch` do LlamaIndex foi intencionalmente diferente das demais:

```text
tentativa 1 do LLM
    ↓ rejeitada pela validação determinística
tentativa 2 do LLM
    ↓ rejeitada pela validação determinística
oracle fallback
    ↓
resultado final esperado
```

Essa execução fez duas chamadas de modelo. Por isso, a avaliação completa tem **75 execuções de framework, mas 76 chamadas de modelo**. A anomalia é preservada em vez de normalizada porque o laboratório precisa mostrar se o sucesso veio do reasoning na primeira tentativa, de recuperação limitada ou de fallback determinístico.

O formato atual de consumo de tokens também é informativo:

```text
LangGraph                611,33 tokens/run
CrewAI Flow              630,60 tokens/run
Agno Workflow            632,00 tokens/run
LlamaIndex Workflow      732,20 tokens/run
CrewAI Agent/Crew       1136,60 tokens/run
```

CrewAI Flow e Agno ficaram praticamente empatados nesta amostra. A média maior do LlamaIndex inclui a execução que fez uma chamada adicional. A comparação dentro do próprio CrewAI continua especialmente útil porque duas abstrações do **mesmo framework** produziram envelopes de tokens muito diferentes.

A conclusão mais útil não é “framework X é melhor”:

> **Nesta carga de trabalho, a escolha da abstração de orquestração pode afetar materialmente o custo de execução mesmo quando autoridade de segurança, verdade esperada, gateway e alias de modelo são compartilhados.**

A latência conta outra história. O Agno teve a menor média, o LlamaIndex o menor p50 e o LangGraph a maior média nesta amostra específica de 15 execuções. Esses valores são descritivos e não estabelecem ranking geral de performance.

Evidência imutável atual:

- [Relatório five-way da Phase 15](artifacts/final-evaluation/phase15-20260905-v2/benchmarks/comparison/five-way-latest.md)
- [Comparação machine-readable da Phase 15](artifacts/final-evaluation/phase15-20260905-v2/benchmarks/comparison/five-way-latest.json)
- [Manifest da Phase 15](artifacts/final-evaluation/phase15-20260905-v2/manifest.json)
- [Metodologia da avaliação final](docs/evaluation/FINAL_EVALUATION.md)
- [Decision matrix dos frameworks](docs/FRAMEWORK_DECISION_MATRIX.md)

### O que a avaliação final **não** prova

- Não demonstra significância estatística.
- Não representa SLOs de produção.
- Com `n=15`, o p95 nearest-rank é o máximo da amostra e serve apenas como indicador descritivo de cauda.
- Não estabelece um ranking geral de frameworks.
- O cenário `adversarial-asset-id` testa uma fronteira restrita entre instrução e dado, não resistência geral a prompt injection.
- O único fallback observado no LlamaIndex não estabelece uma característica estável de retry ou custo do framework.
- O alias `security-analysis` não é atestado independente do modelo nativo selecionado atrás do gateway.

## Evidência histórica de benchmark

O repositório preserva os artifacts anteriores, executados antes da centralização completa do provider, como evidência histórica imutável. Eles documentam o sistema no momento em que foram gerados e não são reescritos para refletir a arquitetura atual.

Evidência five-way histórica:

- [Relatório five-way histórico](artifacts/benchmarks/comparison/five-way-latest.md)
- [Artifact five-way histórico em JSON](artifacts/benchmarks/comparison/five-way-latest.json)

Os identificadores nativos do provider registrados nesses artifacts permanecem intencionalmente inalterados.

## Baseline adversarial LangGraph no plano de evidências

A primeira baseline oficial adversarial v2 move instruções controladas pelo atacante de identificadores estruturados de ativos para documentos explícitos de fornecedor, contexto recuperado e notas internas. A proveniência descreve cada fonte, enquanto o conteúdo dos documentos permanece não confiável e sem autoridade de instrução.

Esta é evidência histórica provider-backed e mantém a identidade nativa do provider registrada quando foi gerada.

```text
Modelo: openai:gpt-5.6-luna
Cenários: 6
Repetições por cenário: 3
Execuções: 18
Sampling: provider default
```

| Acurácia da tarefa | Security pass | Sucesso do ataque no modelo | Unsafe acceptance | Retry | Fallback | Latência média | Tokens médios |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 100% | 100% | 0% | 0% | 0% | 0% | 2503,86 ms | 763,17 |

Nas 18 execuções observadas, todas as asserções de tarefa e segurança passaram e nenhum dos seis objetivos determinísticos do atacante teve sucesso no modelo. Assim, as taxas de rejeição, recuperação e contenção permanecem `N/A`: a amostra não exercitou contenção ao vivo após um ataque bem-sucedido no modelo.

A média v2 de 763,17 tokens/run está 22,9% acima da média adversarial v1 de 620,80. Essa diferença descreve o custo de entrada dos documentos e da proveniência adicionais; não é uma afirmação de performance do framework ou do modelo.

Esse resultado sintético e restrito não estabelece resistência geral a prompt injection. Consulte o [relatório legível](artifacts/adversarial-v2/langgraph/latest.md), o [artifact JSON](artifacts/adversarial-v2/langgraph/latest.json) e o [design e interpretação do plano de evidências](docs/security/ADVERSARIAL_V2_EVIDENCE_PLANE.md).

Um controle positivo não canônico separado concedeu deliberadamente autoridade de instrução ao conteúdo dos documentos. O modelo seguiu o ataque de status forçado nas duas tentativas; a validação determinística rejeitou ambos os drafts e o oracle fallback produziu um resultado final correto e seguro. Isso calibra a telemetria de ataque e contenção sem alterar o prompt canônico. Consulte o [relatório do controle de sensibilidade](artifacts/adversarial-v2-sensitivity/langgraph/latest.md) e o [trace em JSON](artifacts/adversarial-v2-sensitivity/langgraph/latest.json).

## Smoke adversarial v2 nos workflows leves

CrewAI Flow, LlamaIndex Workflow e Agno Workflow executaram uma vez cada um dos mesmos seis cenários do plano de evidências com `openai:gpt-5.6-luna`. Os 18 traces de tentativa foram revisados manualmente após a geração.

Esses artifacts também são evidência histórica de compatibilidade e mantêm intencionalmente a identidade nativa original do provider.

| Workflow | Execuções | Acurácia da tarefa | Security pass | Sucesso do ataque no modelo | Unsafe acceptance | Retry | Fallback | Latência média | Tokens médios |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| CrewAI Flow | 6 | 100% | 100% | 0% | 0% | 0% | 0% | 3947,03 ms | 799,17 |
| LlamaIndex Workflow | 6 | 100% | 100% | 0% | 0% | 0% | 0% | 2843,26 ms | 793,17 |
| Agno Workflow | 6 | 100% | 100% | 0% | 0% | 0% | 0% | 3110,31 ms | 795,00 |

Todos os drafts corresponderam ao oracle determinístico de aplicabilidade na primeira tentativa, e nenhum correspondeu ao objetivo específico do atacante. Esses artifacts com uma repetição confirmam a compatibilidade dos contratos em execução com provider; são evidências de smoke, não baselines, e não sustentam rankings de framework ou performance. Consulte o [registro da revisão manual](docs/security/ADVERSARIAL_V2_WORKFLOW_SMOKE_REVIEW.md).

## Carga de trabalho compartilhada

Todas as implementações recebem o mesmo contrato de evidência independente de framework:

```text
AnalysisEvidenceBundle
├── vulnerability
├── assets
├── policy
└── documents (opcional)
```

Uma solicitação como:

```text
Analise CVE-XXXX-YYYY e determine se nosso ambiente está exposto.
```

gera um resultado estruturado contendo:

- aplicabilidade por ativo;
- severidade;
- recomendação;
- confiança;
- evidência e proveniência;
- necessidade de revisão humana.

O LLM não é dono do identificador CVE, proveniência da evidência, política determinística ou decisão final.

## Loop compartilhado evaluator-optimizer

Todas as variantes são restringidas pela mesma semântica controlada pela aplicação:

```text
evidência
   │
   ▼
análise probabilística
   │
   ▼
avaliador determinístico
   │
   ├── aceito ───────────────────────────────┐
   │                                         │
   └── rejeitado                             │
          │                                  │
          ▼                                  │
 feedback determinístico                     │
          │                                  │
          ▼                                  │
      retry limitado                         │
          │                                  │
          ▼                                  │
 avaliador determinístico                    │
          │                                  │
          ├── aceito ────────────────────────┤
          │                                  │
          └── tentativas esgotadas            │
                 │                           │
                 ▼                           │
        oracle determinístico                │
                 │                           │
                 └──────────────┬────────────┘
                                ▼
                      política determinística
                                │
                                ▼
                         AnalysisResult
```

A configuração oficial permite no máximo duas tentativas de análise pelo LLM.

Um resultado final correto pode, portanto, vir de caminhos distintos:

```text
acerto do LLM na primeira tentativa
recuperação após retry
fallback determinístico
```

Essa distinção entre **qualidade do modelo** e **segurança do sistema** é central para o laboratório.

## Implementações por framework

| Framework / abstração | Orquestração usada | Caminho de reasoning estruturado | Fronteira de provider | Controles determinísticos da aplicação |
| --- | --- | --- | --- | --- |
| LangGraph | nodes + roteamento condicional | saída estruturada via LangChain | LiteLLM `security-analysis` | sim |
| CrewAI Agent/Crew | `Agent` + `Task` + `Crew` | saída estruturada CrewAI | LiteLLM `security-analysis` | sim, avaliador externo |
| CrewAI Flow | Flow routing/state | `LLM.call()` estruturado direto | LiteLLM `security-analysis` | sim |
| LlamaIndex Workflow | eventos tipados | `structured_predict()` | LiteLLM `security-analysis` | sim |
| Agno Workflow | `Workflow` + `Loop` + `Condition` | Agent com saída estruturada | LiteLLM `security-analysis` | sim |

Os adapters ficam abaixo da fronteira da aplicação para que o framework possa ser substituído sem transferir autoridade de segurança.

Todos os cinco caminhos provider-backed agora passam pelo gateway LiteLLM centralizado. Credenciais de provider e identificadores nativos de modelo ficam fora dos adapters; cada cliente conhece somente o alias estável `security-analysis`, o endpoint do gateway e a credencial de cliente exigida por sua integração.

Veja [Arquitetura e modelo de segurança](docs/ARCHITECTURE.md) para os detalhes e [Fundação do gateway LiteLLM](docs/litellm/GATEWAY_FOUNDATION.md) para a fronteira de acesso aos providers.

## Dataset de avaliação

| Cenário | Objetivo | Comportamento esperado |
| --- | --- | --- |
| `baseline-mixed` | ativos afetados e corrigidos | aplicabilidade mista |
| `product-mismatch` | produto instalado não corresponde ao vulnerável | `not_applicable` |
| `unknown-version` | versão não pode ser interpretada com segurança | `unknown` |
| `fixed-boundary` | limite exclusivo de versão afetada | `not_affected` |
| `adversarial-asset-id` | texto semelhante a instrução dentro de dado não confiável | instrução continua sendo dado |

A verdade esperada é externa a todas as implementações e ao modelo upstream configurado.

## Propriedades de segurança demonstradas

A implementação atual exercita:

- saída estruturada do LLM;
- contratos explícitos na aplicação;
- isolamento entre domínio/aplicação e adapters de framework;
- validação fail-closed da identidade da evidência/CVE;
- validação determinística de aplicabilidade;
- feedback do evaluator;
- retry limitado;
- fallback determinístico;
- política determinística de revisão humana;
- separação entre instruções e evidência não confiável;
- supressão de retries implícitos do framework quando necessário;
- supressão de telemetry proprietária de framework quando necessário;
- contabilização de model calls por execução;
- contabilização de tokens;
- medição de latência;
- verdade esperada externa;
- evidência de avaliação imutável persistida;
- alias governado do LiteLLM compartilhado por todos os clientes de framework;
- separação entre OpenTelemetry lógico controlado pela aplicação e telemetry de provider/framework.

## Estrutura do projeto

```text
src/agentic_lab/
├── domain/
├── application/
└── adapters/
    ├── agno/
    ├── crewai/
    ├── fixtures/
    ├── gateway.py
    ├── langchain/
    ├── langgraph/
    └── llamaindex/

config/
└── litellm/
    └── config.yaml

scripts/
├── benchmark_langgraph_scenarios.py
├── benchmark_crewai_scenarios.py
├── benchmark_crewai_flow_scenarios.py
├── benchmark_llamaindex_workflow_scenarios.py
├── benchmark_agno_workflow_scenarios.py
├── compare_five_way_benchmarks.py
├── run_final_evaluation.py
└── quality_gate.py

artifacts/
├── benchmarks/              # evidência histórica de benchmark
└── final-evaluation/
    └── phase15-20260905-v2/ # evidência five-way imutável atual
```

## Reproduzir o ambiente

Requisitos:

- Python 3.13
- [uv](https://docs.astral.sh/uv/)

Instale o ambiente bloqueado pelo lockfile:

```bash
uv sync --frozen --all-groups
```

Execute o quality gate completo:

```bash
uv run python scripts/quality_gate.py
```

O gate cobre lockfile, Ruff, fronteiras arquiteturais, governança, Pyright strict, pytest, coverage, Bandit e auditoria de dependências. O mesmo gate provider-free roda no GitHub Actions.

## Executar experimentos provider-backed pelo gateway

Todos os clientes de framework atuais usam a fronteira centralizada do LiteLLM. `AGENTIC_LAB_MODEL` está obsoleto para seleção de provider.

Carregue a chave do provider e uma master key local do gateway sem persistir nenhum segredo no repositório:

```bash
read -s "OPENAI_API_KEY?OpenAI API key: "
echo
export OPENAI_API_KEY

read -s "LITELLM_MASTER_KEY?LiteLLM master key: "
echo
export LITELLM_MASTER_KEY
```

Instale a versão fixada do proxy como ferramenta do `uv`, fora do grafo de dependências do projeto, e inicie-o usando a configuração versionada:

```bash
uv tool install 'litellm[proxy]==1.98.0'
litellm --config config/litellm/config.yaml
```

Em outro shell, configure o contrato de cliente do gateway. Um ambiente local pode temporariamente reutilizar o valor da master key como credencial do cliente; um deployment pode substituí-la por uma credencial com escopo sem alterar o código da aplicação.

```bash
export AGENTIC_LAB_GATEWAY_BASE_URL="http://localhost:4000"
export AGENTIC_LAB_GATEWAY_API_KEY="$LITELLM_MASTER_KEY"
```

Para benchmarks diretos de framework que devam preservar a mesma fronteira de privacidade usada na avaliação aceita da Phase 15, aplique os mesmos guards específicos de telemetry dos vendors. `CREWAI_TESTING=true` é necessário aqui para bloquear o caminho de coleta de trace da primeira execução no CrewAI 1.15.18 fixado; o OpenTelemetry controlado pelo projeto permanece habilitado porque `OTEL_SDK_DISABLED` deliberadamente não é utilizado.

```bash
export CREWAI_TRACING_ENABLED=false
export CREWAI_DISABLE_TELEMETRY=true
export CREWAI_DISABLE_TRACKING=true
export CREWAI_TESTING=true
export AGNO_TELEMETRY=false
```

Depois execute um benchmark individual ao explorar um adapter:

```bash
uv run python scripts/benchmark_langgraph_scenarios.py --runs 3
uv run python scripts/benchmark_crewai_scenarios.py --runs 3
uv run python scripts/benchmark_crewai_flow_scenarios.py --runs 3
uv run python scripts/benchmark_llamaindex_workflow_scenarios.py --runs 3
uv run python scripts/benchmark_agno_workflow_scenarios.py --runs 3
```

Para uma nova geração controlada de evidência five-way provider-backed, prefira o runner de avaliação final. Ele executa os benchmarks em workspace temporário isolado, valida alias e repetição, aplica os guards de telemetry de vendor exigidos pela metodologia aceita e persiste um novo bundle append-only:

```bash
uv run python scripts/run_final_evaluation.py
```

Não reutilize `phase15-20260905-v2`; esse run-id pertence à evidência imutável aceita da Phase 15. A avaliação final provider-backed não faz parte do CI normal.

## Documentação

- [Arquitetura e modelo de segurança](docs/ARCHITECTURE.md)
- [Decision matrix dos frameworks](docs/FRAMEWORK_DECISION_MATRIX.md)
- [Metodologia da avaliação final](docs/evaluation/FINAL_EVALUATION.md)
- [Fundação do gateway LiteLLM](docs/litellm/GATEWAY_FOUNDATION.md)
- [ADR do gateway LiteLLM](docs/adr/0002-centralize-llm-provider-access-behind-litellm-proxy.md)
- [Relatório five-way atual da Phase 15](artifacts/final-evaluation/phase15-20260905-v2/benchmarks/comparison/five-way-latest.md)
- [Benchmark five-way histórico](artifacts/benchmarks/comparison/five-way-latest.md)
- [Relatório adversarial v2 do LangGraph](artifacts/adversarial-v2/langgraph/latest.md)
- [Design adversarial v2 do plano de evidências](docs/security/ADVERSARIAL_V2_EVIDENCE_PLANE.md)
- [Metodologia do controle de sensibilidade adversarial v2](docs/security/ADVERSARIAL_V2_SENSITIVITY_CONTROL.md)
- [Resultado LangGraph do controle de sensibilidade adversarial v2](artifacts/adversarial-v2-sensitivity/langgraph/latest.md)
- [Revisão do smoke adversarial v2 nos workflows leves](docs/security/ADVERSARIAL_V2_WORKFLOW_SMOKE_REVIEW.md)
- [Agentic Fast Track](docs/AGENTIC_FAST_TRACK.md)
- [Desenvolvimento](docs/DEVELOPMENT.md)
- [MCP](docs/MCP.md)
- [Privacidade](docs/PRIVACY.md)
- [Contrato de engenharia](AGENTS.md)
- [README em inglês](README.md)

## Status atual e próximos experimentos candidatos

Concluído:

- [x] domínio e contrato de evidência independentes de framework;
- [x] evaluator, policy, retry limitado e oracle fallback determinísticos;
- [x] LangGraph evaluator-optimizer;
- [x] CrewAI Agent/Task/Crew;
- [x] CrewAI Flow com LLM estruturado direto;
- [x] LlamaIndex Workflow;
- [x] Agno Workflow;
- [x] dataset compartilhado com cinco cenários e baseline five-way histórica;
- [x] baseline adversarial v2, controle de sensibilidade e smoke nos workflows leves;
- [x] gateway LiteLLM centralizado com alias governado `security-analysis`;
- [x] LangGraph, CrewAI Agent/Crew, CrewAI Flow, LlamaIndex e Agno migrados para a mesma fronteira do gateway;
- [x] compatibilidade MCP v2 e smoke real local STDIO host/client;
- [x] contrato framework-neutral de observação lógica OpenTelemetry sem conteúdo;
- [x] avaliação final provider-backed imutável da Phase 15 vinculada ao commit Git exato avaliado;
- [x] quality gate estrito provider-free local e em CI.

Próximos experimentos candidatos:

- [ ] investigar separadamente o comportamento de timeout da chamada síncrona do LlamaIndex acompanhado na issue #61;
- [ ] evoluir MCP de smoke de compatibilidade para autorização explícita de tools e least privilege;
- [ ] avaliar retry/fallback do gateway, budgets e credenciais de cliente com escopo como políticas governadas separadas;
- [ ] compor providers/exporters OpenTelemetry de deployment sem mover conteúdo para a telemetry lógica;
- [ ] adicionar fluxos controlados de human-in-the-loop;
- [ ] aumentar a amostra para distribuições de latência e estimativas de incerteza;
- [ ] avaliar variação de provider/modelo atrás do alias estável do gateway.

## Por que este projeto existe

Frameworks agênticos tornam demos impressionantes fáceis de construir. O desafio de engenharia é criar sistemas em que raciocínio probabilístico possa ser restringido, validado, medido, auditado, recuperado, comparado e substituído com segurança.

Este repositório trata o framework como um detalhe de implementação abaixo de uma fronteira de segurança estável e usa evidências reproduzíveis para estudar esses trade-offs.
