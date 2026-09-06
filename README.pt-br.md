# Agentic Security Framework Lab

[English](README.md) | [Português (Brasil)](README.pt-br.md)

[![quality](https://github.com/brunovicco/agentic-security-framework-lab/actions/workflows/quality.yml/badge.svg)](https://github.com/brunovicco/agentic-security-framework-lab/actions/workflows/quality.yml)

Um laboratório de engenharia neutro em relação a frameworks para construir, proteger, avaliar e comparar **fluxos de IA agentic** sob os mesmos controles determinísticos.

O projeto implementa a mesma carga de análise de vulnerabilidades com **LangGraph, CrewAI, LlamaIndex e Agno**, roteia o acesso a provedores através do **LiteLLM**, valida o raciocínio do modelo fora do LLM, expõe compatibilidade com **MCP**, emite observações lógicas de **OpenTelemetry** sem conteúdo sensível, e exercita **ações mutáveis governadas de agentes** através de autenticação de posse da aplicação, autorização ciente da fonte de identidade, aprovação humana limitada, autorização do aprovador, execução e fronteiras tipadas de evidência de falha.

> **A ideia central:** frameworks de agentes podem ser donos da orquestração, mas não devem automaticamente ser donos da autoridade de segurança, da política, da evidência, da autorização ou das decisões finais.

## Por que este projeto?

Frameworks agentic tornam protótipos fáceis, mas sistemas de IA de nível produtivo enfrentam um conjunto mais difícil de perguntas:

- O que acontece quando o modelo erra mas o fluxo ainda precisa de um resultado seguro?
- Quais controles devem permanecer determinísticos e independentes de framework?
- Como retries, fallback, fronteiras de ferramentas, telemetria e acesso a provedores permanecem governáveis?
- Como diferentes abstrações de orquestração se comparam quando a carga de trabalho, a verdade esperada, o alias exposto ao modelo e a política de validação são mantidos constantes?
- Como preservar evidência sobre *como* um resultado foi produzido, em vez de reportar apenas acurácia final?
- O que acontece quando um agente pode propor uma ação mutável mas não deve poder autorizar a si mesmo?
- Como identidade do chamador, menor privilégio, aprovação humana e evidência de execução permanecem estáveis quando frameworks ou superfícies de ferramenta mudam?

Este repositório transforma essas perguntas em arquitetura executável, testes, evidência de benchmark e trade-offs explícitos.

## Dicas de leitura

| Público | Comece por aqui | O que dá para avaliar rapidamente |
| --- | --- | --- |
| **Desenvolvedor/Engenheiro de IA** | [Guia de desenvolvimento](docs/DEVELOPMENT.md) → [Arquitetura](docs/ARCHITECTURE.md) | fronteiras, contratos tipados, adapters, retries, fallback, ações governadas, MCP, OTel, reprodutibilidade |
| **Gerente de Engenharia/Arquiteto** | [Visão executiva](docs/EXECUTIVE_OVERVIEW.md) → [Governed Agent Actions](docs/security/GOVERNED_AGENT_ACTIONS.md) | modelo de governança, autorização, fronteira de provedor, trade-offs operacionais, portabilidade entre frameworks, disciplina de evidência |
| **Público Geral** | este README → [Visão executiva](docs/EXECUTIVE_OVERVIEW.md) | escopo do projeto, autoria de engenharia, tecnologias, avaliação mensurável, pensamento de segurança de IA e de plataforma |
| **Segurança/Governança** | [Arquitetura](docs/ARCHITECTURE.md) → [Governed Agent Actions](docs/security/GOVERNED_AGENT_ACTIONS.md) | fronteiras de confiança, menor privilégio, HITL, enforcement em runtime, testes adversariais, MCP, restrições de telemetria/privacidade |

Veja o [mapa completo da documentação](docs/README.md).

## O que o projeto demonstra

### Arquitetura e engenharia de IA

- camadas de Domínio e Aplicação neutras em relação a frameworks;
- adapters de framework abaixo de contratos estáveis da aplicação;
- saída estruturada do LLM com pós-validação determinística;
- laços de controle evaluator-optimizer com retry limitado;
- fallback determinístico por oráculo quando o raciocínio probabilístico é rejeitado;
- separação explícita entre tentativas de análise da aplicação e chamadas reais ao modelo;
- acesso ao modelo neutro em relação ao provedor através de um alias governado no LiteLLM;
- supressão de retries específicos de framework onde retries ocultos distorceriam a evidência ou multiplicariam efeitos colaterais mutáveis;
- artefatos de avaliação imutáveis, produzidos com provedor real e vinculados a um commit Git exato;
- orquestração de ação mutável portável entre LangGraph, CrewAI, LlamaIndex e Agno sem mover a autorização para dentro desses frameworks.

### Segurança e governança

- o LLM raciocina sobre a evidência, mas não é dono da fonte da verdade sensível à segurança;
- identidade e aplicabilidade da evidência são validadas fora do modelo;
- evidência não confiável não tem autoridade de instrução por padrão;
- política determinística controla os requisitos de revisão humana;
- o `ProposedAction`, adjacente ao modelo, é separado do `ActionContext` confiável;
- autenticação do chamador é uma fronteira separada da identidade e da autorização; credenciais brutas não são copiadas para o contexto confiável de ação nem para a evidência de execução;
- a autorização exata de menor privilégio avalia `(caller_id, identity_source, action, resource, environment)` sem fallback entre fontes;
- escopos de ação desconhecidos falham fechado;
- `require_human_approval` permanece bloqueado até que uma evidência de aprovação de origem separada seja validada para o escopo exato de chamador/ação;
- a autoridade de aprovação é limitada, de uso único, revogável antes do claim, com prazo definido e isolada por fonte no provedor controlado;
- a autorização do aprovador verifica de forma independente se o revisor confiável pode aprovar exatamente o escopo requisitado;
- autorização, ciclo de vida da aprovação, autorização do aprovador, execução e autenticação são preservados como fatos de evidência separados;
- exceções pós-executor viram evidência tipada de falha governada com `execution_attempted=true` e `external_side_effect_state=unknown`, sem copiar o texto bruto do executor para a evidência estruturada;
- telemetria proprietária de framework é suprimida onde relevante, para preservar a fronteira de privacidade do projeto;
- o OpenTelemetry lógico contém metadados seguros de execução, não prompts, respostas, justificativas, evidência, credenciais ou payloads de provedor;
- o mapeamento provedor/modelo permanece atrás do gateway em vez de vazar para cada adapter de framework.

### Plataforma e interoperabilidade

- evaluator-optimizer em LangGraph mais `StateGraph` de ação governada;
- CrewAI Agent/Task/Crew;
- CrewAI Flow com chamadas estruturadas diretas ao LLM mais Flow de ação governada;
- LlamaIndex Workflow com eventos tipados mais Workflow de ação governada;
- Agno Workflow com primitivas nativas de loop/condição mais um Step mutável governado sem retry;
- LiteLLM como fronteira centralizada de acesso a provedores;
- compatibilidade com MCP v2 mais smokes reais de host/cliente STDIO local para aplicabilidade somente leitura, ações governadas por composição confiável e um experimento separado de ação governada autenticada com credencial injetada pelo host;
- falhas MCP pós-executor incertas são classificadas como erros de protocolo visíveis ao host, em vez de erros de Tool corrigíveis pelo modelo;
- a conformidade de ação governada entre frameworks, contra o runtime direto da aplicação, cobre tanto estados normais de execução quanto proveniência tipada de falha do executor;
- CI sem provedor para qualidade, tipagem, segurança, compatibilidade MCP, comportamento de ação mutável governada e verificações de contrato de OTel.

## Invariante central

```text
o LLM raciocina
o software valida
a política restringe
o runtime executa
a evidência explica
```

O LLM é um componente de raciocínio probabilístico, não a autoridade final.

Para ações mutáveis, o mesmo princípio se torna:

```text
o agente/modelo propõe
composição confiável ou autenticação estabelece o contexto do chamador
a política autoriza
a evidência humana é reivindicada e validada quando exigida
a política de aprovador valida a autoridade do revisor
o runtime aplica e executa
a evidência registra sucesso ou falha governada
```

E uma distinção permanece explícita em todo o projeto:

```text
disponibilidade da ferramenta != autorização da ferramenta != execução da ferramenta
```

Veja [Governed Agent Actions](docs/security/GOVERNED_AGENT_ACTIONS.md) para o modelo de confiança atual completo.

## Posição sobre prompt injection

Este projeto não tenta impedir prompt injection e não afirma detectá-la.

Ele assume a posição oposta: presuma que a injeção teve sucesso. Presuma que uma evidência não confiável, um documento recuperado, a descrição de uma ferramenta ou um identificador de ativo manipulou com sucesso o raciocínio do modelo. A pergunta que a arquitetura responde é o que isso rende ao atacante.

Na análise somente leitura, rende uma conclusão proposta que um avaliador determinístico vai checar contra evidência externa e rejeitar se estiver errada, com fallback determinístico por oráculo atrás dela.

Em ações mutáveis, rende um `ProposedAction` — dado de proposta não confiável. Não rende identidade do chamador, que é contexto confiável injetado fora da entrada visível ao modelo. Não rende uma decisão de autorização, que é determinística, exata e ciente da fonte de identidade. Não rende evidência de aprovação humana, que tem origem separada e é vinculada ao chamador e ao escopo exatos. Não rende autoridade de aprovador, que é verificada de forma independente. E não rende execução, que só acontece depois de um único ponto de enforcement que avaliou tudo isso.

Uma injeção plenamente bem-sucedida, portanto, produz uma proposta que falha fechado.

O cenário `adversarial-asset-id` e a suíte adversarial v2 de documentos exercitam essa fronteira em pontos específicos. São testes controlados, não prova de resistência ampla a injeção — e sob este modelo de ameaça não é isso que se pede deles. Detecção é uma mitigação. Retirar o modelo do caminho de autoridade é uma propriedade estrutural, e é sobre ela que este repositório é construído.

## Retrato atual do runtime governado — v1.1 até o hardening pós-v1.3

O último release publicado é o **v1.3.0 — Human Approval Lifecycle**. A `main` atual preserva os contratos de ação governada da v1.1 e de identidade confiável de chamador da v1.2, adiciona o ciclo de vida de aprovação da v1.3, e inclui hardening posterior para autorização de aprovador, proveniência tipada de falha de executor, tratamento de execução incerta em MCP e conformidade de falha entre frameworks. Essas mudanças pós-v1.3 são funcionalidade da `main` atual, não alterações retroativas ao release v1.3 publicado.

A fronteira controlada atual inclui:

- `ProposedAction(action, resource, environment)` congelado como dado de proposta não confiável;
- `ActionContext(caller_id, identity_source)` confiável e separado, fornecido por código de composição/runtime ou de autenticação;
- autorização determinística de escopo exato com desfechos `allow`, `deny` e `require_human_approval`;
- `HumanApprovalEvidence` confiável vinculada à proposta e ao contexto de chamador exatos, com validade ciente de fuso horário e semântica de claim de uso único;
- desfechos explícitos de aprovação para estados ausente, revogado, inválido, aprovador não autorizado, ainda não válido, expirado e validado;
- autorização separada de aprovador para o escopo exato `(approver_id, caller_id, identity_source, action, resource, environment)`;
- uma composição de autenticação de chamador de serviço que estabelece contexto de chamador `api_key` fora da entrada de modelo/ferramenta, antes da autorização ciente da fonte;
- `GovernedActionRuntime` como ponto único de enforcement antes da execução mutável;
- `ActionExecutionEvidence` separando autorização, ciclo de vida da aprovação, autorização do aprovador e a execução propriamente dita;
- `ActionExecutionFailureEvidence` e `AuthenticatedActionExecutionFailureEvidence` para proveniência de falha pós-executor sem afirmar se um efeito colateral externo foi efetivado;
- um adapter mutável e seguro, em memória, de reconhecimento de finding;
- adapters de framework para LangGraph, CrewAI Flow, LlamaIndex Workflow e Agno Workflow;
- testes adversariais para spoofing de chamador, aprovações falsas, substituição de ferramenta, escalação de escopo e retry após negação;
- conformidade entre frameworks comparando evidência completa de sucesso/falha e comportamento observável do executor com a execução direta da aplicação;
- um servidor MCP STDIO mutável governado cujo schema de ferramenta não pode fornecer identidade confiável de chamador ou de aprovação;
- um experimento MCP STDIO autenticado separado, com credencial injetada pelo host, cuja credencial bruta permanece fora dos argumentos de ferramenta visíveis ao modelo e da evidência estruturada;
- classificação de erro de protocolo MCP para falhas pós-executor incertas, de modo que um estado desconhecido de efeito colateral não retorne pelo canal normal de resultado de Tool corrigível pelo modelo;
- execução mutável em Agno com `max_retries=0` e preservação do `GovernedActionExecutionError` original através do `RunStatus.error` do framework.

A matriz de conformidade entre frameworks cobre allow exato, deny explícito, aprovação ausente/validada, aprovador não autorizado, aprovação expirada/revogada, divergência de chamador, divergência de fonte de identidade, escalação de recurso e falha de executor autorizado. Para todos os frameworks, a evidência de execução normal e a evidência de falha pós-executor devem coincidir com a baseline direta da aplicação, com exatamente uma tentativa de executor no cenário controlado de falha.

Isto é **evidência de integração aplicação/framework/MCP sem provedor**. Não afirma identidade autenticada de usuário remoto, OAuth/OIDC/JWT/mTLS, aprovações duráveis ou distribuídas, infraestrutura de IAM/política de nível produtivo, idempotência, rollback/compensação, execução de ação com provedor real, evidência de auditoria assinada/à prova de adulteração, nem certificação de produção.

## Retrato da avaliação v1.0 — custo e caminho de execução sob acurácia constante

A avaliação aceita da Fase 15 executa cinco variantes de orquestração contra o mesmo conjunto de cenários através do mesmo alias governado do LiteLLM.

```text
Alias de cliente governado: security-analysis
Cenários: 5
Repetições por cenário: 3
Execuções por variante: 15
Execuções de framework: 75
Chamadas reais ao modelo: 76
Commit avaliado: dd48c2490fc4ec1c76093577f7944d76a6fbc572
```

Todas as cinco variantes de orquestração chegaram ao resultado final esperado sob os mesmos controles de posse da aplicação. A acurácia é, portanto, constante na comparação e não é um discriminador — é a condição de controle, não o achado.

O que variou foi custo e caminho de execução. A comparação dentro do CrewAI é o caso mais claro: `Agent + Task + Crew` e `Flow` resolveram a mesma carga dentro do mesmo framework com envelopes de token materialmente diferentes nesta amostra. A execução `product-mismatch` do LlamaIndex é o outro:

```text
tentativa 1 do LLM → rejeitada
tentativa 2 do LLM → rejeitada
fallback determinístico por oráculo → resultado final esperado
```

Essa execução é o motivo de 75 execuções de framework terem produzido **76 chamadas reais ao modelo**, e é o mais útil dos dois resultados. Um benchmark que reportasse apenas acurácia final mostraria cinco linhas idênticas e esconderia o fato de que uma delas chegou lá por um caminho diferente. O laboratório preserva essa anomalia porque evidência sobre comportamento de recuperação vale mais do que uma saída de benchmark cosmeticamente uniforme.

| Variante | Tokens médios | Latência média | Chamadas médias ao modelo | Aceitação de primeira passagem | Acurácia final esperada |
| --- | --- | --- | --- | --- | --- |
| LangGraph evaluator-optimizer | **611,33** | 3404,92 ms | 1,00 | 100% | 100% |
| CrewAI Agent + Task + Crew | 1136,60 | 2987,15 ms | 1,00 | 100% | 100% |
| CrewAI Flow + LLM estruturado direto | 630,60 | 3172,98 ms | 1,00 | 100% | 100% |
| LlamaIndex Workflow + `structured_predict()` | 732,20 | 3214,98 ms | **1,07** | **93,33%** | 100% |
| Agno Workflow + `Loop`/`Condition` nativos | 632,00 | **2980,14 ms** | 1,00 | 100% | 100% |

### O que estes números não provam

- Não estabelecem significância estatística nem SLOs de produção.
- Quinze execuções por variante não bastam para rankings universais de latência.
- Os resultados não provam que um framework seja superior de forma geral.
- Os cenários adversariais são testes controlados, não prova de resistência ampla a prompt injection.
- O alias `security-analysis` é uma identidade de cliente governada, não uma atestação independente do modelo nativo do provedor selecionado atrás do gateway.

Evidência canônica:

- [Relatório five-way da Fase 15](artifacts/final-evaluation/phase15-20260905-v2/benchmarks/comparison/five-way-latest.md)
- [Comparação legível por máquina](artifacts/final-evaluation/phase15-20260905-v2/benchmarks/comparison/five-way-latest.json)
- [Manifesto da avaliação](artifacts/final-evaluation/phase15-20260905-v2/manifest.json)
- [Metodologia da avaliação final](docs/evaluation/FINAL_EVALUATION.md)

Artefatos históricos obtidos diretamente com o provedor permanecem imutáveis e intencionalmente não são reescritos para refletir hardening posterior de gateway ou runtime.

## Implementações por framework

### Carga de análise

| Framework/abstração | Orquestração nativa | Caminho de raciocínio estruturado | Fronteira de provedor | Autoridade determinística |
| --- | --- | --- | --- | --- |
| LangGraph | nós de grafo + roteamento condicional | saída estruturada do LangChain | LiteLLM `security-analysis` | Aplicação |
| CrewAI Agent/Crew | `Agent` + `Task` + `Crew` | saída estruturada do CrewAI | LiteLLM `security-analysis` | Avaliador da aplicação |
| CrewAI Flow | roteamento/estado de Flow | `LLM.call()` estruturado direto | LiteLLM `security-analysis` | Aplicação |
| LlamaIndex Workflow | eventos tipados de Workflow | `structured_predict()` | LiteLLM `security-analysis` | Aplicação |
| Agno Workflow | `Workflow` + `Loop` + `Condition` | saída estruturada do Agent | LiteLLM `security-analysis` | Aplicação |

### Ação mutável governada

| Framework | Papel do framework | Contexto confiável | Dono da autorização/enforcement |
| --- | --- | --- | --- |
| LangGraph | um nó de ação no grafo | injetado fora da entrada do grafo | `GovernedActionRuntime` |
| CrewAI Flow | um start determinístico de Flow | dependência de construtor, fora do estado do Flow | `GovernedActionRuntime` |
| LlamaIndex Workflow | um step de evento tipado | dependência de construtor, fora do StartEvent | `GovernedActionRuntime` |
| Agno Workflow | um Step Python customizado | dependência injetada, fora da entrada do workflow | `GovernedActionRuntime` |

Os frameworks são deliberadamente adapters, não donos das regras de negócio/segurança. Veja a [matriz de decisão de frameworks](docs/FRAMEWORK_DECISION_MATRIX.md) para os trade-offs observados na carga de análise e [Governed Agent Actions](docs/security/GOVERNED_AGENT_ACTIONS.md) para a fronteira de ação mutável.

## Fronteiras de confiança e de provedor

```text
Adapter de framework
     │
     │ alias estável: security-analysis
     ▼
Gateway LiteLLM
     │
     │ mapeamento de provedor de posse do deployment
     ▼
Provedor de LLM
```

Os clientes de framework conhecem o alias estável e o contrato do gateway. Identificadores nativos de provedor e credenciais de provedor permanecem fora do caminho de negócio específico de cada framework.

Separadamente, ações mutáveis governadas usam um caminho de autoridade diferente:

```text
proposta de ação não confiável
     +
contexto confiável de chamador
     │
     ▼
autorização da aplicação
     │
     ├─ deny ──────────────────────► evidência/sem execução
     │
     ├─ exige aprovação ─► validação de aprovação confiável
     │                         │
     │                         └─ ausente/inválida ─► sem execução
     ▼
GovernedActionRuntime
     │
     ▼
adapter mutável
```

A telemetria lógica de posse da aplicação descreve fatos seguros de execução da análise sem exportar automaticamente conteúdo do modelo:

```text
Execução da aplicação
     │
     ▼
AnalysisExecutionObservation
     │ apenas atributos seguros em allowlist
     ▼
composição de OpenTelemetry de posse do deployment
```

Leia [Arquitetura](docs/ARCHITECTURE.md), [Governed Agent Actions](docs/security/GOVERNED_AGENT_ACTIONS.md), [Fundação do gateway LiteLLM](docs/litellm/GATEWAY_FOUNDATION.md) e [Privacidade](docs/PRIVACY.md) para as fronteiras detalhadas.

## Fronteira MCP

O projeto mantém separadas as preocupações versionadas de leitura e de mutação por composição confiável, mais um experimento autenticado isolado usado por testes de compatibilidade/smoke:

```text
agentic-security-applicability                  # superfície de análise/aplicabilidade somente leitura
agentic-security-governed-actions               # superfície de ação mutável por composição confiável
agentic-security-authenticated-governed-actions # experimento autenticado com injeção pelo host; não registrado no projeto
```

Para a ferramenta mutável governada:

- `resource` e `environment` são argumentos de ferramenta não confiáveis;
- `action` é fixado pelo handler;
- o `caller_id` local controlado é injetado por código de composição confiável do servidor;
- `caller_id`, `approval_id` e `approver_id` não são argumentos de ferramenta;
- anotações de ferramenta são metadados, não autorização;
- a evidência de execução retornada é conferida contra uma ferramenta separada de estado somente leitura no smoke STDIO real;
- o experimento autenticado recebe material de credencial sintético apenas do ambiente confiável de host/processo e o mantém fora do schema da Tool;
- depois que um executor governado foi invocado e lança exceção, os servidores de composição confiável e autenticado mapeiam apenas a falha governada tipada para uma falha de protocolo `MCPError` com evidência segura;
- essa classificação de protocolo impede que esse estado incerto de efeito colateral vire um canal comum de retry `CallToolResult(is_error=true)` visível ao modelo, mas não impede que um host implemente seu próprio retry programático.

Os experimentos MCP locais intencionalmente não são descritos como identidade autenticada de usuário remoto, identidade vinculada ao transporte, IAM de produção ou autorização de produção. `external_side_effect_state=unknown` é preservado mesmo quando o fixture controlado observa zero mutação.

## Início rápido para desenvolvedores

Requisitos:

- Python 3.13
- [uv](https://docs.astral.sh/uv/)

```bash
git clone https://github.com/brunovicco/agentic-security-framework-lab.git
cd agentic-security-framework-lab
uv sync --frozen --all-groups
uv run python scripts/quality_gate.py
```

O quality gate normal roda sem provedor. Você **não** precisa de uma chave de API de LLM para validar os contratos de engenharia, testes, tipagem, verificações de arquitetura, verificações de segurança, comportamento de ação governada, compatibilidade MCP ou comportamento determinístico.

Para desenvolvimento focado:

```bash
uv run python scripts/quality_gate.py --list
```

Para experimentos com provedor real através do LiteLLM, siga o [guia de fundação do gateway](docs/litellm/GATEWAY_FOUNDATION.md) e a [metodologia da avaliação final](docs/evaluation/FINAL_EVALUATION.md). A avaliação final com provedor é intencionalmente separada do CI normal.

Leia o [guia de desenvolvimento](docs/DEVELOPMENT.md) completo antes de alterar adapters de framework, contratos de autorização/runtime, evidência de avaliação, política de gateway, ferramentas MCP ou contratos de telemetria.

## Mapa do repositório

```text
src/agentic_lab/
├── domain/          # conceitos e invariantes de negócio neutros em relação a frameworks
├── application/     # casos de uso, semântica de avaliador/política/autorização, ports
└── adapters/        # LangGraph, CrewAI, LlamaIndex, Agno, integrações de gateway/ação

config/litellm/      # configuração governada de acesso a provedores
scripts/             # benchmarks, avaliação, quality gates, servidores/smokes MCP
docs/                # arquitetura, ADRs, segurança, avaliação, MCP, privacidade
artifacts/           # evidência imutável de benchmark/avaliação
tests/               # cobertura de regressão, adversarial, conformidade e contrato, sem provedor
```

## Mapa da documentação

### Entender o projeto rapidamente

- [Documentação por público](docs/README.md)
- [Visão executiva/de portfólio](docs/EXECUTIVE_OVERVIEW.md)
- [Arquitetura e fronteiras de confiança](docs/ARCHITECTURE.md)
- [Governed Agent Actions](docs/security/GOVERNED_AGENT_ACTIONS.md)
- [Matriz de decisão de frameworks](docs/FRAMEWORK_DECISION_MATRIX.md)

### Construir e alterar o código

- [Guia de desenvolvimento](docs/DEVELOPMENT.md)
- [Contrato de engenharia](AGENTS.md)
- [Trilha rápida agentic](docs/AGENTIC_FAST_TRACK.md)

### Avaliar e reproduzir evidência

- [Metodologia da avaliação final](docs/evaluation/FINAL_EVALUATION.md)
- [Evidência five-way atual](artifacts/final-evaluation/phase15-20260905-v2/benchmarks/comparison/five-way-latest.md)
- [Manifesto da avaliação](artifacts/final-evaluation/phase15-20260905-v2/manifest.json)
- [Conformidade de ação governada entre frameworks](tests/integration/test_governed_action_framework_conformance.py)

### Segurança, privacidade e interoperabilidade

- [Governed Agent Actions](docs/security/GOVERNED_AGENT_ACTIONS.md)
- [Fronteira de privacidade](docs/PRIVACY.md)
- [Experimentos de segurança](docs/security)
- [Visão geral de MCP](docs/MCP.md)
- [Fundação do gateway LiteLLM](docs/litellm/GATEWAY_FOUNDATION.md)
- [Registros de decisão de arquitetura](docs/adr)

## O que torna isto um projeto de portfólio e não um demo de framework

O repositório é intencionalmente construído em torno de decisões de engenharia que sobrevivem à substituição do framework:

1. **Domínio, política, autorização e enforcement permanecem neutros em relação a frameworks.**
2. **Saída probabilística é validada por software determinístico.**
3. **Um modelo pode propor uma ação mutável, mas não pode autorizar a si mesmo.**
4. **Comportamento de falha é observável em vez de oculto.**
5. **Acesso a provedores é centralizado atrás de uma fronteira estável.**
6. **Telemetria tem um contrato explícito de privacidade.**
7. **Evidência de benchmark é persistida e vinculada ao estado do código-fonte.**
8. **Trade-offs são documentados em vez de reduzidos a "o framework X venceu."**

Essas são as partes pensadas para serem reutilizáveis ao raciocinar sobre plataformas corporativas de agentes, gateways de IA, runtimes governados, LLMOps, segurança de IA, autorização, MCP ou seleção de frameworks.

## Status do projeto

O escopo de engenharia planejado da **v1.0** está completo: baseline de domínio, controles determinísticos, progressão de RAG, quatro famílias de framework/cinco variantes de orquestração, comparação de benchmark, LiteLLM, MCP, observabilidade, avaliação final, hardening de runtime e documentação de portfólio.

Os marcos publicados pós-v1.0 são **v1.1 Governed Agent Actions**, **v1.2 Trusted Caller Identity** e **v1.3 Human Approval Lifecycle**. A `main` atual adicionalmente endurece a autorização de aprovador, a evidência de falha de executor governada, a composição de falha autenticada, o tratamento de transporte para execução incerta em MCP, a preservação de proveniência de falha no Agno e a conformidade de falha entre frameworks.

Isto continua sendo um laboratório de engenharia, não uma alegação de certificação de produção. Aprovação durável/distribuída, identidade remota vinculada ao transporte, IAM de produção, idempotência/rollback, transacionalidade de efeito colateral externo e infraestrutura de auditoria assinada/à prova de adulteração permanecem não-objetivos explícitos até que um experimento concreto os exija. Cada uma dessas fronteiras está registrada como um registro de decisão de arquitetura, com o desenho pretendido e os gatilhos de reavaliação, em vez de ficar como omissão não examinada. Evidência histórica com provedor real e metadados de releases publicados não são reescritos pelo hardening da `main` atual.

Veja o [CHANGELOG.md](CHANGELOG.md) para mudanças em nível de release.
