# Agentic Security Framework Lab

[![quality](https://github.com/brunovicco/agentic-security-framework-lab/actions/workflows/quality.yml/badge.svg)](https://github.com/brunovicco/agentic-security-framework-lab/actions/workflows/quality.yml)

Um laboratório controlado de engenharia para comparar **LangGraph, CrewAI, LlamaIndex e Agno** usando a mesma carga de trabalho sensível à segurança.

O projeto busca responder a uma pergunta prática e deliberadamente restrita:

> O que muda quando diferentes abstrações de orquestração agêntica resolvem o mesmo problema sob as mesmas evidências, verdade esperada, validação determinística, retry, fallback, política e modelo?

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

## Benchmark five-way

O benchmark oficial atual compara cinco variantes de orquestração usando o mesmo modelo e os mesmos cinco cenários.

```text
Modelo: openai:gpt-5.6-luna
Cenários: 5
Repetições por cenário: 3
Execuções por variante: 15
Sampling: provider default
```

| Variante | Acurácia esperada | First pass | Média de calls | Latência média | p50 | Tokens médios |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| LangGraph evaluator-optimizer | 100% | 100% | 1,00 | **2728,01 ms** | **2643,41 ms** | **613,80** |
| CrewAI Agent + Task + Crew | 100% | 100% | 1,00 | 2866,79 ms | 2818,60 ms | 1143,33 |
| CrewAI Flow + LLM estruturado direto | 100% | 100% | 1,00 | 2847,78 ms | 2739,98 ms | 630,27 |
| LlamaIndex Workflow + `structured_predict()` | 100% | 100% | 1,00 | 2963,03 ms | 2837,52 ms | 630,13 |
| Agno Workflow + `Loop` / `Condition` | 100% | 100% | 1,00 | 3268,84 ms | 3159,27 ms | 634,20 |

### O principal achado

Para esta carga de trabalho controlada, as três variantes leves adicionadas depois da baseline LangGraph convergiram para envelopes de tokens quase idênticos:

```text
LlamaIndex Workflow   630,13 tokens/run
CrewAI Flow           630,27 tokens/run
Agno Workflow         634,20 tokens/run
```

O spread entre elas é de apenas **0,65%**.

Já o envelope `Agent + Task + Crew` do CrewAI consumiu **1143,33 tokens/run**.

Trocar essa abstração por CrewAI Flow removeu **96,89%** do excesso de tokens do Agent/Crew acima da baseline LangGraph. LlamaIndex removeu **96,92%** e Agno, **96,15%**.

A conclusão mais útil não é “framework X é melhor”:

> **Nesta carga de trabalho, a escolha da abstração de orquestração teve mais impacto no custo de tokens do que a diferença entre as implementações leves dos frameworks.**

A latência conta outra história. O Agno permaneceu no mesmo cluster leve de tokens, mas apresentou latência média e p50 maiores nesta amostra de 15 execuções. Esses valores são descritivos, não um ranking geral de performance.

Evidências completas:

- [Relatório five-way](artifacts/benchmarks/comparison/five-way-latest.md)
- [Artifact five-way em JSON](artifacts/benchmarks/comparison/five-way-latest.json)
- [Decision matrix dos frameworks](docs/FRAMEWORK_DECISION_MATRIX.md)

### O que o benchmark não prova

- Não demonstra significância estatística.
- Não representa SLOs de produção.
- Com `n=15`, o p95 nearest-rank é o máximo da amostra e serve apenas como indicador descritivo de cauda.
- Não estabelece um ranking geral de frameworks.
- O cenário `adversarial-asset-id` testa uma fronteira restrita entre instrução e dado, não resistência geral a prompt injection.
- Todas as variantes oficiais chegaram a 100% de first-pass acceptance nesta execução, portanto não há evidência para ranking de qualidade.

## Baseline adversarial LangGraph no plano de evidências

A primeira baseline oficial adversarial v2 move instruções controladas pelo atacante de identificadores estruturados de ativos para documentos explícitos de fornecedor, contexto recuperado e notas internas. A proveniência descreve cada fonte, enquanto o conteúdo dos documentos permanece não confiável e sem autoridade de instrução.

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

| Framework / abstração | Orquestração usada | Caminho de reasoning estruturado | Controles determinísticos da aplicação |
| --- | --- | --- | --- |
| LangGraph | nodes + roteamento condicional | saída estruturada via LangChain | sim |
| CrewAI Agent/Crew | `Agent` + `Task` + `Crew` | saída estruturada CrewAI | sim, avaliador externo |
| CrewAI Flow | Flow routing/state | `LLM.call()` estruturado direto | sim |
| LlamaIndex Workflow | eventos tipados | `structured_predict()` | sim |
| Agno Workflow | `Workflow` + `Loop` + `Condition` | Agent com saída estruturada | sim |

Os adapters ficam abaixo da fronteira da aplicação para que o framework possa ser substituído sem transferir autoridade de segurança.

Veja [Arquitetura e modelo de segurança](docs/ARCHITECTURE.md) para os detalhes.

## Dataset de avaliação

| Cenário | Objetivo | Comportamento esperado |
| --- | --- | --- |
| `baseline-mixed` | ativos afetados e corrigidos | aplicabilidade mista |
| `product-mismatch` | produto instalado não corresponde ao vulnerável | `not_applicable` |
| `unknown-version` | versão não pode ser interpretada com segurança | `unknown` |
| `fixed-boundary` | limite exclusivo de versão afetada | `not_affected` |
| `adversarial-asset-id` | texto semelhante a instrução dentro de dado não confiável | instrução continua sendo dado |

A verdade esperada é externa a todas as implementações e ao modelo.

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
- desativação de telemetry de framework quando necessário;
- contabilização de model calls por execução;
- contabilização de tokens;
- medição de latência;
- verdade esperada externa;
- artifacts persistidos de benchmark.

## Estrutura do projeto

```text
src/agentic_lab/
├── domain/
├── application/
└── adapters/
    ├── agno/
    ├── crewai/
    ├── fixtures/
    ├── langchain/
    ├── langgraph/
    └── llamaindex/

scripts/
├── benchmark_langgraph_scenarios.py
├── benchmark_crewai_scenarios.py
├── benchmark_crewai_flow_scenarios.py
├── benchmark_llamaindex_workflow_scenarios.py
├── benchmark_agno_workflow_scenarios.py
├── compare_five_way_benchmarks.py
└── quality_gate.py

artifacts/benchmarks/
├── langgraph/
├── crewai/
├── crewai-flow/
├── llamaindex-workflow/
├── agno-workflow/
└── comparison/
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

O gate cobre lockfile, Ruff, fronteiras arquiteturais, governança, Pyright strict, pytest, coverage, Bandit e auditoria de dependências. O mesmo gate roda no GitHub Actions.

## Executar benchmarks com provider real

Configure o modelo sem colocar credenciais no repositório:

```bash
export AGENTIC_LAB_MODEL="openai:gpt-5.6-luna"
```

Carregue a API key sem exibi-la:

```bash
read -s "OPENAI_API_KEY?OpenAI API key: "
echo
export OPENAI_API_KEY
```

Exemplos:

```bash
uv run python scripts/benchmark_langgraph_scenarios.py --runs 3
uv run python scripts/benchmark_langgraph_adversarial_v2.py --runs 3
uv run python scripts/benchmark_crewai_scenarios.py --runs 3
uv run python scripts/benchmark_crewai_flow_scenarios.py --runs 3
uv run python scripts/benchmark_llamaindex_workflow_scenarios.py --runs 3
AGNO_TELEMETRY=false uv run python scripts/benchmark_agno_workflow_scenarios.py --runs 3
```

Regere a comparação consolidada:

```bash
uv run python scripts/compare_five_way_benchmarks.py
```

## Documentação

- [Arquitetura e modelo de segurança](docs/ARCHITECTURE.md)
- [Decision matrix dos frameworks](docs/FRAMEWORK_DECISION_MATRIX.md)
- [Benchmark five-way](artifacts/benchmarks/comparison/five-way-latest.md)
- [Relatório adversarial v2 do LangGraph](artifacts/adversarial-v2/langgraph/latest.md)
- [Design adversarial v2 do plano de evidências](docs/security/ADVERSARIAL_V2_EVIDENCE_PLANE.md)
- [Metodologia do controle de sensibilidade adversarial v2](docs/security/ADVERSARIAL_V2_SENSITIVITY_CONTROL.md)
- [Resultado LangGraph do controle de sensibilidade adversarial v2](artifacts/adversarial-v2-sensitivity/langgraph/latest.md)
- [Agentic Fast Track](docs/AGENTIC_FAST_TRACK.md)
- [Desenvolvimento](docs/DEVELOPMENT.md)
- [MCP](docs/MCP.md)
- [Privacidade](docs/PRIVACY.md)
- [Contrato de engenharia](AGENTS.md)
- [README em inglês](README.md)

## Status atual e próximos experimentos

Concluído:

- [x] domínio e contrato de evidência independentes de framework;
- [x] evaluator, policy, retry e oracle fallback determinísticos;
- [x] LangGraph evaluator-optimizer;
- [x] CrewAI Agent/Task/Crew;
- [x] CrewAI Flow com LLM estruturado direto;
- [x] LlamaIndex Workflow;
- [x] Agno Workflow;
- [x] dataset compartilhado com cinco cenários;
- [x] benchmark oficial de 15 execuções para cada variante;
- [x] comparação five-way persistida;
- [x] fronteira explícita de proveniência e autoridade de instrução para documentos de evidência;
- [x] baseline oficial LangGraph adversarial v2 com 18 execuções;
- [x] controle de sensibilidade não canônico com provider e contenção por fallback observada;
- [x] binding compartilhado de documentos de evidência e telemetria de tentativas nos workflows leves;
- [x] quality gate estrito local e em CI.

Próximos experimentos candidatos:

- [ ] reutilizar a suíte adversarial v2 nas variantes leves dos frameworks;
- [ ] comparar modelos/providers sob os mesmos controles;
- [ ] explorar MCP, autorização de tools e least privilege;
- [ ] comparar tracing e observabilidade;
- [ ] adicionar fluxos controlados de human-in-the-loop;
- [ ] aumentar a amostra para análise de latência e incerteza.

## Por que este projeto existe

Frameworks agênticos tornam demos impressionantes fáceis de construir. O desafio de engenharia é criar sistemas em que raciocínio probabilístico possa ser restringido, validado, medido, auditado, recuperado, comparado e substituído com segurança.

Este repositório trata o framework como um detalhe de implementação abaixo de uma fronteira de segurança estável e usa evidências reproduzíveis para estudar esses trade-offs.
