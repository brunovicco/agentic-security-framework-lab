# Agentic Security Framework Lab

[![quality](https://github.com/brunovicco/agentic-security-framework-lab/actions/workflows/quality.yml/badge.svg)](https://github.com/brunovicco/agentic-security-framework-lab/actions/workflows/quality.yml)

Um laboratório independente de framework para construir, proteger, avaliar e comparar sistemas de IA agêntica usando a mesma carga de trabalho de análise de vulnerabilidades.

O projeto foi criado para responder a uma pergunta prática:

> Como diferentes frameworks agênticos se comportam quando precisam resolver o mesmo problema sensível de segurança, usando os mesmos contratos, evidências, dataset de avaliação e controles de runtime?

A implementação atual usa **LangChain** para abstração de modelos e saída estruturada do LLM, e **LangGraph** para orquestração.

Estão planejadas implementações equivalentes com CrewAI, LlamaIndex e Agno.

## Princípio central

```text
LLM raciocina
software valida
política restringe
runtime executa
evidência explica
```

O LLM é tratado como um componente probabilístico de raciocínio, e não como a autoridade final do sistema.

O software determinístico permanece responsável por validação, aplicação de políticas, fallback e decisões sensíveis de segurança.

## Caso de uso

A carga de trabalho compartilhada é a análise de vulnerabilidades:

```text
Analise CVE-XXXX-YYYY e determine se nosso ambiente está exposto.
```

O sistema recebe evidências sobre a vulnerabilidade e inventário de ativos e produz um resultado estruturado contendo:

- aplicabilidade por ativo;
- severidade;
- recomendação;
- confiança;
- evidências e proveniência;
- necessidade de revisão humana.

## Arquitetura

O projeto mantém domínio e contratos de aplicação independentes dos frameworks de orquestração.

```text
                  Domínio
                    │
                    ▼
                Aplicação
                    │
                    ▼
            Portas / Contratos
                    │
        ┌───────────┴───────────┐
        │                       │
        ▼                       ▼
Adapters de framework     Avaliação compartilhada
        │
        ├── LangChain
        ├── LangGraph
        ├── CrewAI       planejado
        ├── LlamaIndex   planejado
        └── Agno         planejado
```

O workflow atual em LangGraph implementa o padrão **evaluator-optimizer**:

```text
evidência
   │
   ▼
análise do LLM
   │
   ▼
avaliador determinístico
   │
   ├── aceito
   └── rejeitado
          │
          ▼
 feedback do avaliador
          │
          ▼
     retry do LLM
          │
          ▼
avaliador determinístico
          │
          ├── aceito
          └── rejeitado
                 │
                 ▼
       fallback determinístico
                 │
                 ▼
       política determinística
                 │
                 ▼
          AnalysisResult
```

O workflow permite no máximo duas tentativas de análise pelo LLM antes de recorrer ao fallback determinístico.

## Evidência independente de framework

Os motores agênticos consomem o mesmo contrato de evidência no nível da aplicação:

```text
AnalysisEvidenceBundle
├── vulnerability
├── assets
└── policy
```

A evidência injetada segue uma política **fail-closed** para a identidade da vulnerabilidade: um bundle cujo identificador CVE não corresponda à entrada do grafo é rejeitado antes da análise pelo LLM.

Esse limite foi projetado para ser reutilizado nas futuras implementações com outros frameworks.

## Dataset de avaliação

O dataset inicial contém cinco cenários.

| Cenário | Objetivo | Comportamento esperado |
| --- | --- | --- |
| `baseline-mixed` | ativos afetados e corrigidos | aplicabilidade mista |
| `product-mismatch` | produto instalado diferente do produto vulnerável | `not_applicable` |
| `unknown-version` | versão não pode ser interpretada com segurança | `unknown` |
| `fixed-boundary` | limite exclusivo da versão afetada | `not_affected` |
| `adversarial-asset-id` | texto semelhante a instrução inserido em dado não confiável | instrução permanece sendo tratada como dado |

O cenário adversarial é propositalmente restrito. Ele testa uma fronteira entre **instrução e dado** e **não** deve ser interpretado como prova de resistência geral a prompt injection.

## Benchmark atual com LangGraph

O benchmark persistido foi executado com:

```text
Framework: LangGraph
Padrão: evaluator-optimizer
Modelo: openai:gpt-5.6-luna
Cenários: 5
Execuções por cenário: 3
Total de execuções: 15
```

### Resultados

| Métrica | Resultado |
| --- | ---: |
| Acurácia esperada | 100,0% |
| Aceitação na primeira tentativa | 100,0% |
| Taxa de retry | 0,0% |
| Taxa de recuperação | N/A |
| Taxa de fallback | 0,0% |
| Média de chamadas ao modelo | 1,00 |
| Latência média | 2728,01 ms |
| Latência p50 | 2643,41 ms |
| Latência p95 | 3526,02 ms |
| Média de tokens por execução | 613,80 |
| Total de tokens | 9207 |

Todos os 15 resultados finais corresponderam à verdade esperada definida pelo dataset independente de framework.

O cenário adversarial também produziu o resultado esperado nas três execuções, sem retry e sem fallback determinístico.

A recuperação é apresentada como `N/A` porque nenhuma execução precisou entrar no caminho de retry do evaluator-optimizer.

Essas medições representam um benchmark de engenharia com amostragem pequena. Os percentis de latência não devem ser interpretados como SLOs de produção.

Evidências completas do benchmark:

- [`artifacts/benchmarks/langgraph/latest.md`](artifacts/benchmarks/langgraph/latest.md)
- [`artifacts/benchmarks/langgraph/latest.json`](artifacts/benchmarks/langgraph/latest.json)

## Propriedades de segurança

A implementação atual demonstra diversos controles de segurança para sistemas agênticos:

- saída estruturada do LLM;
- contratos explícitos na camada de aplicação;
- oracle determinístico de aplicabilidade;
- aplicação determinística de políticas;
- roteamento condicional de validação;
- feedback do avaliador;
- retry limitado;
- fallback determinístico;
- validação fail-closed da identidade da evidência;
- separação entre instruções e evidências não confiáveis;
- verdade esperada externa para avaliação;
- evidência do caminho de execução em runtime;
- medição de tokens e latência.

Um resultado final correto não significa necessariamente que o LLM tenha acertado.

Por exemplo:

```text
tentativa 1 do LLM: errada
tentativa 2 do LLM: errada
        │
        ▼
fallback determinístico
        │
        ▼
resultado final do sistema: correto
```

A distinção entre **qualidade do modelo** e **segurança do sistema** é um dos princípios centrais deste projeto.

## Estrutura do projeto

```text
src/agentic_lab/
├── domain/
├── application/
└── adapters/
    ├── fixtures/
    ├── langchain/
    └── langgraph/

tests/
└── unit/

scripts/
├── benchmark_langgraph.py
├── benchmark_langgraph_scenarios.py
├── run_llm_demo.py
└── quality_gate.py

artifacts/
└── benchmarks/
    └── langgraph/
        ├── latest.json
        └── latest.md

docs/
├── AGENTIC_FAST_TRACK.md
├── ARCHITECTURE.md
└── DEVELOPMENT.md
```

## Requisitos

- Python 3.13
- [uv](https://docs.astral.sh/uv/)

Instale o ambiente usando o lockfile:

```bash
uv sync --frozen --all-groups
```

## Quality gate

Execute o gate completo de engenharia localmente:

```bash
uv run python scripts/quality_gate.py
```

O gate cobre:

- consistência do lockfile;
- lint com Ruff;
- formatação com Ruff;
- validação de fronteiras arquiteturais;
- tipagem estrita com Pyright;
- testes com pytest;
- limite mínimo de cobertura;
- análise estática com Bandit;
- auditoria de vulnerabilidades em dependências.

O mesmo quality gate é executado no GitHub Actions.

## Executar o demo determinístico/LLM

Configure um modelo:

```bash
export AGENTIC_LAB_MODEL="openai:<model-id>"
```

Carregue a API key sem exibi-la no terminal:

```bash
read -s "OPENAI_API_KEY?OpenAI API key: "
echo
export OPENAI_API_KEY
```

Execute:

```bash
uv run python scripts/run_llm_demo.py
```

A saída expõe decisões importantes do runtime:

```text
analysis_source
validation_passed
validation_reason
analysis_attempts
```

seguidas pelo `AnalysisResult` estruturado.

## Executar o benchmark de cenário único

```bash
uv run python scripts/benchmark_langgraph.py --runs 5
```

Esse benchmark coleta métricas como:

- taxa de aceitação;
- taxa de retry;
- taxa de fallback;
- latência;
- uso de tokens;
- chamadas ao modelo;
- confiança.

## Executar o benchmark multi-cenário

Execute cada cenário de avaliação três vezes:

```bash
uv run python scripts/benchmark_langgraph_scenarios.py --runs 3
```

O benchmark produz evidências legíveis por máquina e por humanos:

```text
artifacts/benchmarks/langgraph/latest.json
artifacts/benchmarks/langgraph/latest.md
```

## Documentação

- [Agentic Fast Track](docs/AGENTIC_FAST_TRACK.md)
- [Arquitetura](docs/ARCHITECTURE.md)
- [Desenvolvimento](docs/DEVELOPMENT.md)
- [Contrato de engenharia](AGENTS.md)

## Roadmap

### Concluído

- [x] fundação determinística para análise de vulnerabilidades;
- [x] abstração de modelos com LangChain;
- [x] análise estruturada usando LLM;
- [x] workflow determinístico em LangGraph;
- [x] evaluator-optimizer em LangGraph;
- [x] validação determinística e fallback;
- [x] dataset de avaliação independente de framework;
- [x] cenário adversarial de fronteira entre instrução e dado;
- [x] benchmarks de latência e tokens;
- [x] persistência das evidências de benchmark.

### Próximos passos

- [ ] implementação com CrewAI;
- [ ] benchmark comparativo entre frameworks;
- [ ] implementação com LlamaIndex;
- [ ] implementação com Agno;
- [ ] comparação entre providers e modelos;
- [ ] expansão do dataset adversarial;
- [ ] integração MCP e autorização de ferramentas;
- [ ] observabilidade e correlação de traces;
- [ ] workflows human-in-the-loop.

## Por que este projeto existe

Frameworks agênticos tornam relativamente simples construir demos impressionantes.

O problema de engenharia mais difícil é criar sistemas em que o raciocínio probabilístico possa ser:

- restringido;
- validado;
- medido;
- auditado;
- recuperado;
- comparado;
- substituído com segurança.

Este repositório é um laboratório de aprendizado e engenharia para explorar esses trade-offs usando uma carga de trabalho consistente e sensível à segurança.
