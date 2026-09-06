from pathlib import Path


def replace_once(path: str, old: str, new: str, label: str) -> None:
    file_path = Path(path)
    text = file_path.read_text()
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, found {count}")
    file_path.write_text(text.replace(old, new, 1))


# README.md
replace_once(
    "README.md",
    "It implements the same vulnerability-analysis workload with **LangGraph, CrewAI, LlamaIndex, and Agno**, routes provider access through **LiteLLM**, validates model reasoning outside the LLM, exposes **MCP** compatibility, emits content-free logical **OpenTelemetry** observations, and now exercises **governed mutable agent actions** through the same application-owned authorization and enforcement boundary.",
    "It implements the same vulnerability-analysis workload with **LangGraph, CrewAI, LlamaIndex, and Agno**, routes provider access through **LiteLLM**, validates model reasoning outside the LLM, exposes **MCP** compatibility, emits content-free logical **OpenTelemetry** observations, and exercises **governed mutable agent actions** through application-owned authentication, source-aware authorization, bounded human approval, approver authorization, execution, and typed failure-evidence boundaries.",
    "README intro",
)

replace_once(
    "README.md",
    "- exact least-privilege authorization evaluates `(caller_id, identity_source, action, resource, environment)` with no cross-source fallback;\n- unknown action scopes fail closed;\n- `require_human_approval` remains blocked until separately sourced approval evidence is validated for the exact caller/action scope;\n- authorization, approval, and actual execution are recorded as independent evidence facts;",
    "- caller authentication is a separate boundary from caller identity and authorization; raw credentials are not copied into trusted action context or execution evidence;\n- exact least-privilege authorization evaluates `(caller_id, identity_source, action, resource, environment)` with no cross-source fallback;\n- unknown action scopes fail closed;\n- `require_human_approval` remains blocked until separately sourced approval evidence is validated for the exact caller/action scope;\n- approval authority is bounded, single-use, revocable before claim, time-limited, and source-isolated in the controlled provider;\n- approver authorization independently verifies whether the trusted reviewer may approve the exact requested scope;\n- authorization, approval lifecycle, approver authorization, execution, and authentication are preserved as separate evidence facts;\n- post-executor exceptions become typed governed failure evidence with `execution_attempted=true` and `external_side_effect_state=unknown`, without copying raw executor text into structured evidence;",
    "README security capabilities",
)

replace_once(
    "README.md",
    "- MCP v2 compatibility plus real local STDIO host/client smokes for read-only applicability and governed mutable actions;\n- cross-framework governed-action conformance against the direct application runtime;",
    "- MCP v2 compatibility plus real local STDIO host/client smokes for read-only applicability, trusted-composition governed actions, and a separate host-injected authenticated governed-action experiment;\n- uncertain post-executor MCP failures are classified as host-visible protocol errors instead of normal model-correctable Tool errors;\n- cross-framework governed-action conformance against the direct application runtime covers both normal execution states and typed executor-failure provenance;",
    "README platform capabilities",
)

replace_once(
    "README.md",
    "agent/model proposes\ntrusted context identifies the caller\npolicy authorizes\nhuman evidence approves when required\nruntime enforces\nadapter executes\nevidence proves what happened",
    "agent/model proposes\ntrusted composition or authentication establishes caller context\npolicy authorizes\nhuman evidence is claimed and validated when required\napprover policy validates reviewer authority\nruntime enforces and executes\nevidence records success or governed failure",
    "README mutable invariant",
)

replace_once(
    "README.md",
    "See [Governed Agent Actions](docs/security/GOVERNED_AGENT_ACTIONS.md) for the complete v1.1 trust model.\n\n## v1.1 engineering snapshot — Governed Agent Actions\n\nThe post-v1.0 work extends the original principle from **analysis decisions** into **mutable agent actions** without changing who owns security authority.",
    "See [Governed Agent Actions](docs/security/GOVERNED_AGENT_ACTIONS.md) for the complete current trust model.\n\n## Current governed-runtime snapshot — v1.1 through post-v1.3 hardening\n\nThe latest published release is **v1.3.0 — Human Approval Lifecycle**. Current `main` preserves the v1.1 governed-action and v1.2 trusted-caller-identity contracts, adds the v1.3 approval lifecycle, and includes subsequent hardening for approver authorization, typed executor-failure provenance, MCP uncertain-execution handling, and cross-framework failure conformance. These post-v1.3 changes are current-main functionality, not retroactive changes to the published v1.3 release.",
    "README current snapshot heading",
)

replace_once(
    "README.md",
    "- trusted `HumanApprovalEvidence` bound to the exact proposal and caller context;\n- `GovernedActionRuntime` as the single enforcement point before mutable execution;\n- `ActionExecutionEvidence` separating authorization, approval state, and actual execution;",
    "- trusted `HumanApprovalEvidence` bound to the exact proposal and caller context, with timezone-aware validity and single-use claim semantics;\n- explicit approval outcomes for missing, revoked, invalid, unauthorized approver, not-yet-valid, expired, and validated states;\n- separate approver authorization for the exact `(approver_id, caller_id, identity_source, action, resource, environment)` scope;\n- a service-caller authentication composition that establishes `api_key` caller context outside model/tool input before source-aware authorization;\n- `GovernedActionRuntime` as the single enforcement point before mutable execution;\n- `ActionExecutionEvidence` separating authorization, approval lifecycle, approver authorization, and actual execution;\n- `ActionExecutionFailureEvidence` and `AuthenticatedActionExecutionFailureEvidence` for post-executor failure provenance without claiming whether an external side effect committed;",
    "README governed boundary capabilities",
)

replace_once(
    "README.md",
    "- cross-framework conformance comparing complete evidence and observable side effects with direct application execution;\n- a separate governed mutable MCP STDIO server whose tool schema cannot provide trusted caller or approval identity.\n\nThe cross-framework conformance matrix covers exact allow, explicit deny, missing approval, validated trusted approval, caller mismatch, identity-source mismatch, and resource escalation. For every framework, the expected security semantics and side-effect count must match the direct application baseline.\n\nThis is **provider-free application/framework/MCP integration evidence**. It does not claim authenticated remote identity, production-grade authorization infrastructure, provider-backed action execution, or production certification.",
    "- cross-framework conformance comparing complete success/failure evidence and observable executor behavior with direct application execution;\n- a governed mutable MCP STDIO server whose tool schema cannot provide trusted caller or approval identity;\n- a separate host-injected authenticated MCP STDIO experiment whose raw credential remains outside model-visible tool arguments and structured evidence;\n- MCP protocol-error classification for uncertain post-executor failures so that an unknown side-effect state is not returned through the normal model-correctable Tool-result channel;\n- Agno mutable execution with `max_retries=0` and preservation of the original `GovernedActionExecutionError` across framework `RunStatus.error`.\n\nThe cross-framework conformance matrix covers exact allow, explicit deny, missing/validated approval, unauthorized approver, expired/revoked approval, caller mismatch, identity-source mismatch, resource escalation, and authorized executor failure. For every framework, normal execution evidence and post-executor failure evidence must match the direct application baseline, with exactly one executor attempt in the controlled failure scenario.\n\nThis is **provider-free application/framework/MCP integration evidence**. It does not claim authenticated remote-user identity, OAuth/OIDC/JWT/mTLS, durable or distributed approvals, production-grade IAM/policy infrastructure, idempotency, rollback/compensation, provider-backed action execution, signed/tamper-proof audit evidence, or production certification.",
    "README current conformance scope",
)

replace_once(
    "README.md",
    "The project keeps two local MCP concerns separate:\n\n```text\nagentic-security-applicability      # read-only analysis/applicability surface\nagentic-security-governed-actions   # controlled mutable-action surface\n```",
    "The project keeps checked-in read-only and trusted-composition mutable concerns separate, plus one isolated authenticated experiment used by compatibility/smoke tests:\n\n```text\nagentic-security-applicability                 # read-only analysis/applicability surface\nagentic-security-governed-actions              # trusted-composition mutable-action surface\nagentic-security-authenticated-governed-actions # host-injected authenticated experiment; not project-registered\n```",
    "README MCP servers",
)

replace_once(
    "README.md",
    "- returned execution evidence is checked against a separate read-only state tool in the real STDIO smoke.\n\nThe local MCP experiment is intentionally not described as authenticated remote-user identity or production authorization.",
    "- returned execution evidence is checked against a separate read-only state tool in the real STDIO smoke;\n- the authenticated experiment receives synthetic credential material only from the trusted host/process environment and keeps it out of the Tool schema;\n- after a governed executor has been invoked and raises, the trusted-composition and authenticated servers map only the typed governed failure to an `MCPError` protocol failure with safe evidence;\n- that protocol classification prevents this uncertain side-effect state from becoming an ordinary model-visible `CallToolResult(is_error=true)` retry channel, but it does not prevent a host from implementing its own programmatic retry.\n\nThe local MCP experiments are intentionally not described as authenticated remote-user identity, transport-bound identity, production IAM, or production authorization. `external_side_effect_state=unknown` is preserved even when the controlled fixture observes zero mutation.",
    "README MCP behavior",
)

replace_once(
    "README.md",
    "The planned **v1.0** engineering scope is complete: domain baseline, deterministic controls, RAG progression, four framework families / five orchestration variants, benchmark comparison, LiteLLM, MCP, observability, final evaluation, runtime hardening, and portfolio documentation.\n\nPost-v1.0 development is extending the lab with **v1.1 Governed Agent Actions**: application-owned exact-scope authorization, trusted caller context, controlled HITL approval evidence, runtime enforcement, safe mutable execution, four-framework conformance, and a governed local MCP action boundary.\n\nThis remains an engineering lab, not a claim of production certification. Future work can extend identity, policy, approval durability, external side effects, and audit infrastructure without rewriting the accepted historical v1.0 evidence.",
    "The planned **v1.0** engineering scope is complete: domain baseline, deterministic controls, RAG progression, four framework families / five orchestration variants, benchmark comparison, LiteLLM, MCP, observability, final evaluation, runtime hardening, and portfolio documentation.\n\nPublished post-v1.0 milestones are **v1.1 Governed Agent Actions**, **v1.2 Trusted Caller Identity**, and **v1.3 Human Approval Lifecycle**. Current `main` additionally hardens approver authorization, governed executor-failure evidence, authenticated failure composition, MCP uncertain-execution transport handling, Agno failure-provenance preservation, and cross-framework failure conformance.\n\nThis remains an engineering lab, not a claim of production certification. Durable/distributed approval, remote transport-bound identity, production IAM, idempotency/rollback, external side-effect transactionality, and signed/tamper-proof audit infrastructure remain explicit non-goals until a concrete experiment requires them. Historical provider-backed evidence and published release metadata are not rewritten by current-main hardening.",
    "README project status",
)

# README.pt-br.md
replace_once(
    "README.pt-br.md",
    "O projeto implementa a mesma carga de análise de vulnerabilidades com **LangGraph, CrewAI, LlamaIndex e Agno**, centraliza acesso a providers com **LiteLLM**, valida o raciocínio do modelo fora do LLM, demonstra compatibilidade **MCP**, emite observações lógicas de **OpenTelemetry** sem conteúdo sensível e agora também exercita **ações mutáveis governadas** por uma mesma fronteira de autorização e enforcement da Application.",
    "O projeto implementa a mesma carga de análise de vulnerabilidades com **LangGraph, CrewAI, LlamaIndex e Agno**, centraliza acesso a providers com **LiteLLM**, valida o raciocínio do modelo fora do LLM, demonstra compatibilidade **MCP**, emite observações lógicas de **OpenTelemetry** sem conteúdo sensível e exercita **ações mutáveis governadas** por fronteiras da Application para autenticação, autorização source-aware, aprovação humana limitada, autorização do aprovador, execução e evidence tipada de falha.",
    "README pt intro",
)

replace_once(
    "README.pt-br.md",
    "- autorização least-privilege avalia exatamente `(caller_id, identity_source, action, resource, environment)`, sem fallback entre origens de identidade;\n- scopes desconhecidos falham de forma fechada;\n- `require_human_approval` continua bloqueado até existir evidência de aprovação confiável para exatamente o mesmo caller e action scope;\n- autorização, aprovação e execução real são preservadas como fatos distintos de evidence;",
    "- autenticação do caller é uma fronteira separada de identidade e autorização; credenciais brutas não são copiadas para o contexto confiável nem para execution evidence;\n- autorização least-privilege avalia exatamente `(caller_id, identity_source, action, resource, environment)`, sem fallback entre origens de identidade;\n- scopes desconhecidos falham de forma fechada;\n- `require_human_approval` continua bloqueado até existir evidência de aprovação confiável para exatamente o mesmo caller e action scope;\n- a autoridade de approval é limitada no tempo, single-use, revogável antes do claim e isolada por origem de identidade no provider controlado;\n- autorização do aprovador verifica separadamente se o reviewer confiável pode aprovar exatamente o scope solicitado;\n- autenticação, autorização, ciclo de approval, approver authorization e execução são preservados como fatos separados;\n- exceções depois da chamada ao executor geram failure evidence tipada com `execution_attempted=true` e `external_side_effect_state=unknown`, sem copiar texto bruto da exceção para evidence estruturada;",
    "README pt security capabilities",
)

replace_once(
    "README.pt-br.md",
    "- compatibilidade MCP v2 mais smokes reais locais STDIO para applicability read-only e governed mutable actions;\n- conformance cross-framework de governed actions contra a execução direta da Application;",
    "- compatibilidade MCP v2 mais smokes reais locais STDIO para applicability read-only, governed actions por trusted composition e um experimento autenticado separado com credencial injetada pelo host;\n- falhas MCP incertas após a chamada ao executor são classificadas como erros de protocolo visíveis ao host, e não como Tool errors normais corrigíveis pelo modelo;\n- conformance cross-framework de governed actions contra a execução direta da Application cobre estados normais e provenance tipada de falha do executor;",
    "README pt platform capabilities",
)

replace_once(
    "README.pt-br.md",
    "agente/modelo propõe\ncontexto confiável identifica o caller\npolítica autoriza\nevidência humana aprova quando necessário\nruntime aplica enforcement\nadapter executa\nevidência prova o que aconteceu",
    "agente/modelo propõe\ntrusted composition ou autenticação estabelece o caller context\npolítica autoriza\nevidência humana é claimed e validada quando necessário\npolicy de aprovador valida a autoridade do reviewer\nruntime aplica enforcement e executa\nevidência registra sucesso ou falha governada",
    "README pt mutable invariant",
)

replace_once(
    "README.pt-br.md",
    "Leia [Governed Agent Actions](docs/security/GOVERNED_AGENT_ACTIONS.md) para o trust model completo da v1.1.\n\n## Snapshot de engenharia v1.1 — Governed Agent Actions\n\nO desenvolvimento pós-v1.0 estende o princípio original de **decisões de análise** para **ações mutáveis de agentes** sem mudar quem possui a autoridade de segurança.",
    "Leia [Governed Agent Actions](docs/security/GOVERNED_AGENT_ACTIONS.md) para o trust model completo atual.\n\n## Snapshot atual do governed runtime — v1.1 ao hardening pós-v1.3\n\nA release publicada mais recente é **v1.3.0 — Human Approval Lifecycle**. O `main` atual preserva os contratos de v1.1 Governed Agent Actions e v1.2 Trusted Caller Identity, adiciona o approval lifecycle de v1.3 e inclui hardening posterior para approver authorization, provenance tipada de falha do executor, tratamento de uncertain execution no MCP e conformance cross-framework de falhas. Essas mudanças pós-v1.3 pertencem ao `main` atual e não reescrevem retroativamente a release v1.3 publicada.",
    "README pt current snapshot heading",
)

replace_once(
    "README.pt-br.md",
    "- `HumanApprovalEvidence` confiável vinculada exatamente à proposta e ao caller context;\n- `GovernedActionRuntime` como único enforcement point antes da execução mutável;\n- `ActionExecutionEvidence` separando decisão, status de aprovação e execução real;",
    "- `HumanApprovalEvidence` confiável vinculada exatamente à proposta e ao caller context, com validade timezone-aware e claim single-use;\n- outcomes explícitos de approval para missing, revoked, invalid, unauthorized approver, not-yet-valid, expired e validated;\n- approver authorization separada para o scope exato `(approver_id, caller_id, identity_source, action, resource, environment)`;\n- composição de autenticação de service caller que estabelece contexto `api_key` fora do input de modelo/tool antes da autorização source-aware;\n- `GovernedActionRuntime` como único enforcement point antes da execução mutável;\n- `ActionExecutionEvidence` separando authorization, approval lifecycle, approver authorization e execução real;\n- `ActionExecutionFailureEvidence` e `AuthenticatedActionExecutionFailureEvidence` para provenance pós-executor sem afirmar se o side effect externo foi committed;",
    "README pt governed boundary capabilities",
)

replace_once(
    "README.pt-br.md",
    "- conformance cross-framework comparando evidence completa e side effects observáveis com a execução direta da Application;\n- um servidor MCP STDIO mutável separado, cujo schema não permite ao modelo fornecer identidade de caller ou aprovação confiável.\n\nA matriz de conformance cobre allow exato, deny explícito, approval ausente, approval confiável validado, caller mismatch, identity-source mismatch e resource escalation. Em todos os frameworks, os mesmos security semantics e a mesma contagem de side effects devem coincidir com a baseline direta da Application.\n\nIsso é **evidência provider-free de integração entre Application, frameworks e MCP local**. Não é uma afirmação de identidade remota autenticada, infraestrutura de autorização production-grade, action execution provider-backed ou certificação de produção.",
    "- conformance cross-framework comparando evidence completa de sucesso/falha e comportamento observável do executor com a execução direta da Application;\n- servidor MCP STDIO mutável governado cujo schema não permite ao modelo fornecer identidade de caller ou approval confiável;\n- experimento MCP STDIO autenticado separado, com credencial injetada pelo host e fora dos argumentos visíveis ao modelo e da evidence estruturada;\n- classificação de erro de protocolo MCP para falhas incertas pós-executor, evitando devolver `external_side_effect_state=unknown` pelo canal normal de Tool error corrigível pelo modelo;\n- execução mutável no Agno com `max_retries=0` e preservação do `GovernedActionExecutionError` original através de `RunStatus.error`.\n\nA matriz de conformance cobre allow exato, deny explícito, approval missing/validated, unauthorized approver, approval expired/revoked, caller mismatch, identity-source mismatch, resource escalation e falha autorizada do executor. Em todos os frameworks, evidence de execução normal e failure evidence pós-executor devem coincidir com a baseline direta da Application, com exatamente uma tentativa do executor no cenário controlado de falha.\n\nIsso é **evidência provider-free de integração entre Application, frameworks e MCP local**. Não é uma afirmação de identidade remota autenticada, OAuth/OIDC/JWT/mTLS, approval durável/distribuído, IAM/policy production-grade, idempotência, rollback/compensation, execução mutável provider-backed, audit evidence assinada/tamper-proof ou certificação de produção.",
    "README pt current conformance scope",
)

replace_once(
    "README.pt-br.md",
    "O projeto mantém duas preocupações locais de MCP separadas:\n\n```text\nagentic-security-applicability      # superfície read-only de análise/applicability\nagentic-security-governed-actions   # superfície controlada de ação mutável\n```",
    "O projeto mantém separadas as superfícies locais checked-in de leitura e ação mutável por trusted composition, além de um experimento autenticado isolado usado por testes de compatibilidade/smoke:\n\n```text\nagentic-security-applicability                  # superfície read-only de análise/applicability\nagentic-security-governed-actions               # ação mutável por trusted composition\nagentic-security-authenticated-governed-actions # experimento autenticado host-injected; não registrado no projeto\n```",
    "README pt MCP servers",
)

replace_once(
    "README.pt-br.md",
    "- execution evidence retornada é verificada contra uma Tool read-only separada no smoke STDIO real.\n\nO experimento MCP local intencionalmente não é descrito como identidade autenticada de usuário remoto nem como autorização de produção.",
    "- execution evidence retornada é verificada contra uma Tool read-only separada no smoke STDIO real;\n- o experimento autenticado recebe material sintético de credencial somente do ambiente confiável do host/processo e o mantém fora do Tool schema;\n- depois que o executor governado foi chamado e lança uma exceção, os servidores trusted-composition e autenticado mapeiam apenas a falha governada tipada para `MCPError` com evidence segura;\n- essa classificação evita que o estado incerto seja devolvido como `CallToolResult(is_error=true)` comum e usado como canal natural de retry dirigido pelo modelo, mas não impede um host de implementar retry programático.\n\nOs experimentos MCP locais intencionalmente não são descritos como identidade autenticada de usuário remoto, identidade vinculada ao transporte, IAM de produção ou autorização production-grade. `external_side_effect_state=unknown` permanece `unknown` mesmo quando a fixture controlada observa zero mutações.",
    "README pt MCP behavior",
)

replace_once(
    "README.pt-br.md",
    "O escopo planejado de engenharia da **v1.0** está completo: baseline de domínio, controles determinísticos, progressão de RAG, quatro famílias de framework / cinco variantes de orquestração, comparação de benchmark, LiteLLM, MCP, observabilidade, avaliação final, runtime hardening e documentação de portfólio.\n\nO desenvolvimento pós-v1.0 está estendendo o laboratório com **v1.1 Governed Agent Actions**: autorização application-owned por scope exato, caller context confiável, approval HITL controlado, runtime enforcement, execução mutável segura, conformance em quatro frameworks e uma fronteira MCP local governada.\n\nEste continua sendo um laboratório de engenharia, não uma afirmação de certificação de produção. Trabalho futuro pode estender identidade, policy, durabilidade de approval, side effects externos e infraestrutura de auditoria sem reescrever a evidência histórica aceita da v1.0.",
    "O escopo planejado de engenharia da **v1.0** está completo: baseline de domínio, controles determinísticos, progressão de RAG, quatro famílias de framework / cinco variantes de orquestração, comparação de benchmark, LiteLLM, MCP, observabilidade, avaliação final, runtime hardening e documentação de portfólio.\n\nOs milestones pós-v1.0 publicados são **v1.1 Governed Agent Actions**, **v1.2 Trusted Caller Identity** e **v1.3 Human Approval Lifecycle**. O `main` atual também endurece approver authorization, governed executor-failure evidence, composição autenticada de falha, tratamento MCP de uncertain execution, preservação de failure provenance no Agno e conformance cross-framework de falhas.\n\nEste continua sendo um laboratório de engenharia, não uma afirmação de certificação de produção. Approval durável/distribuído, identidade remota vinculada ao transporte, IAM de produção, idempotência/rollback, transacionalidade de side effects externos e audit evidence assinada/tamper-proof permanecem non-goals explícitos até existir um experimento concreto que os exija. Evidência provider-backed histórica e metadata de releases publicadas não são reescritas pelo hardening do `main` atual.",
    "README pt project status",
)

# docs/README.md
replace_once(
    "docs/README.md",
    "- application-owned action authorization and runtime enforcement;\n- trusted caller context and exact least-privilege scopes;",
    "- application-owned caller authentication, action authorization and runtime enforcement;\n- trusted caller context and exact source-aware least-privilege scopes;\n- bounded single-use approval lifecycle, revocation and independent approver authorization;\n- typed executor-failure evidence and explicit unknown external side-effect state;",
    "docs map developer focus",
)

replace_once(
    "docs/README.md",
    "- how trusted human approval is kept outside model-controlled inputs;\n- how provider access can be centralized;",
    "- how trusted human approval is kept outside model-controlled inputs and constrained by lifecycle/approver authority;\n- how executor failures preserve authority provenance without claiming external side-effect outcome;\n- how provider access can be centralized;",
    "docs map manager focus",
)

replace_once(
    "docs/README.md",
    "- exact caller/action/resource/environment authorization;\n- human approval as separately sourced evidence;",
    "- exact caller/identity-source/action/resource/environment authorization;\n- caller authentication as a distinct source of trusted context;\n- human approval lifecycle plus separate approver authorization;\n- post-executor failure evidence with `external_side_effect_state=unknown`;",
    "docs map security focus",
)

replace_once(
    "docs/README.md",
    "The v1.1 governed-action documentation describes provider-free CI and local MCP integration evidence. It does not rewrite or expand the accepted v1.0 provider-backed evaluation bundle.",
    "Governed-runtime documentation now spans the published v1.1 Governed Agent Actions, v1.2 Trusted Caller Identity, v1.3 Human Approval Lifecycle milestones and post-v1.3 current-main hardening for approver authorization, executor-failure provenance, MCP uncertain-execution handling and cross-framework failure conformance. These documents describe provider-free CI/local integration evidence and do not rewrite or expand the accepted v1.0 provider-backed evaluation bundle or published release metadata.",
    "docs map evidence distinction",
)

# docs/EXECUTIVE_OVERVIEW.md
replace_once(
    "docs/EXECUTIVE_OVERVIEW.md",
    "All current provider-backed paths use a centralized LiteLLM gateway alias, while deterministic application code remains responsible for validating evidence, applicability, fallback, and final policy.",
    "All current provider-backed analysis paths use a centralized LiteLLM gateway alias, while deterministic application code remains responsible for validating evidence, applicability, fallback, and final policy. Separately, governed mutable actions keep caller authentication, source-aware authorization, human-approval lifecycle, approver authorization, execution, and failure evidence outside framework/model authority.\n\nThe latest published release is **v1.3.0 — Human Approval Lifecycle**. Current `main` includes additional provider-free hardening after that release; the documentation distinguishes those current-main capabilities from immutable published release metadata.",
    "executive intro current state",
)

replace_once(
    "docs/EXECUTIVE_OVERVIEW.md",
    "### 7. Interoperability boundaries\n\nThe project includes MCP v2 compatibility and a real local STDIO host/client smoke, while keeping MCP transport concerns outside the Domain layer.",
    "### 7. Governed mutable actions and least privilege\n\nA model or agent can propose a mutable action, but trusted caller context and application policy decide whether it is authorized. Exact policy scope includes caller identity source, action, resource, and environment, with unknown scope failing closed.\n\n### 8. Trusted caller identity and bounded human approval\n\nService-caller authentication is composed before authorization and keeps raw credentials out of model-visible Tool input and execution evidence. Human approval is separately sourced, exact-bound, time-limited, single-use, revocable before claim, and independently checked against approver authorization.\n\n### 9. Failure provenance instead of false certainty\n\nOnce a mutable executor is invoked, an exception does not prove whether an external side effect committed. The application therefore emits typed `ActionExecutionFailureEvidence` with `execution_attempted=true` and `external_side_effect_state=unknown`; authenticated composition preserves the successful authentication decision alongside that governed failure.\n\n### 10. Interoperability and MCP failure boundaries\n\nThe project includes MCP v2 compatibility and real local STDIO host/client smokes for read-only applicability, trusted-composition governed actions, and an isolated host-injected authenticated action experiment. Post-executor governed failures are mapped to MCP protocol errors rather than ordinary model-correctable Tool errors, while MCP transport concerns remain outside the Domain layer.",
    "executive management capabilities",
)

replace_once(
    "docs/EXECUTIVE_OVERVIEW.md",
    "## v1.0 evaluation evidence",
    "## Current governed-runtime evidence\n\nProvider-free CI and integration tests currently prove:\n\n- authentication rejection stops before authorization and mutable execution;\n- source-aware authorization does not inherit authority across `identity_source` values;\n- explicit deny is terminal and human approval cannot override it;\n- approval claims distinguish missing, revoked, invalid, unauthorized approver, temporal failure and validated states;\n- approval authority is single-use and process-local claim/revoke transitions are synchronized in the controlled provider;\n- executor failure preserves the authority chain and records external side-effect state as `unknown`;\n- LangGraph, CrewAI Flow, LlamaIndex Workflow and Agno Workflow match the direct application baseline for governed execution and executor-failure provenance;\n- Agno's mutable Step uses `max_retries=0` and preserves the original governed failure across workflow error status;\n- governed MCP STDIO surfaces uncertain executor failures as protocol errors with safe evidence, not ordinary model-directed Tool retry results.\n\nThis evidence does not claim production IAM, remote transport-bound identity, durable/distributed approval, external transactionality, idempotency/compensation, or signed/tamper-proof audit storage.\n\n## v1.0 evaluation evidence",
    "executive current governed evidence",
)

replace_once(
    "docs/EXECUTIVE_OVERVIEW.md",
    "- secure-by-design trust boundaries;\n- LLM gateway patterns;\n- retries and fallback ownership;\n- MCP integration boundaries;",
    "- secure-by-design trust boundaries;\n- caller authentication, source-aware least privilege, HITL lifecycle and approver authorization;\n- typed execution-failure provenance and unknown side-effect handling;\n- LLM gateway patterns;\n- retries and fallback ownership;\n- MCP integration and uncertain-execution boundaries;",
    "executive portfolio bullets",
)

replace_once(
    "docs/EXECUTIVE_OVERVIEW.md",
    "| architecture and trust boundaries | [ARCHITECTURE.md](ARCHITECTURE.md) |",
    "| architecture and trust boundaries | [ARCHITECTURE.md](ARCHITECTURE.md) |\n| governed authentication, authorization, approval and failure evidence | [security/GOVERNED_AGENT_ACTIONS.md](security/GOVERNED_AGENT_ACTIONS.md) |",
    "executive reading table",
)

# docs/ARCHITECTURE.md
replace_once(
    "docs/ARCHITECTURE.md",
    "- exact-scope action authorization;\n- trusted human-approval contracts;\n- governed runtime enforcement;\n- `ActionExecutionEvidence`.",
    "- service-caller authentication and trusted identity provenance;\n- exact source-aware action authorization;\n- trusted human-approval lifecycle contracts;\n- independent approver authorization;\n- governed runtime enforcement;\n- `ActionExecutionEvidence`, `ActionExecutionFailureEvidence`, authenticated execution evidence, and authenticated governed failure evidence.",
    "architecture application responsibilities",
)

replace_once(
    "docs/ARCHITECTURE.md",
    "The v1.1 governed-action work currently relies on provider-free CI/integration evidence. It does not rewrite the accepted v1.0 provider-backed benchmark artifacts.",
    "The post-v1.0 governed-runtime work — including published v1.1/v1.2/v1.3 milestones and subsequent current-main hardening — relies on provider-free CI/integration evidence. It does not rewrite the accepted v1.0 provider-backed benchmark artifacts or published release metadata.",
    "architecture benchmark evidence scope",
)

replace_once(
    "docs/ARCHITECTURE.md",
    "| trusted caller identity/context | deployment/composition boundary | no |\n| action authorization outcome | application policy | no |\n| whether HITL approval is required | application policy | no |\n| trusted approval evidence | approval provider / trusted integration | no |\n| whether the mutable executor is reached | `GovernedActionRuntime` | no |\n| orchestration mechanics | framework adapter | yes |",
    "| presented caller credential | trusted host/process boundary | no |\n| caller authentication decision | application authenticator | no |\n| trusted caller identity/context | deployment/composition or successful authentication boundary | no |\n| action authorization outcome | application policy | no |\n| whether HITL approval is required | application policy | no |\n| trusted approval evidence / lifecycle state | approval provider / trusted integration | no |\n| whether a reviewer may approve the exact scope | approver authorization policy | no |\n| whether the mutable executor is reached | `GovernedActionRuntime` | no |\n| post-executor failure classification/evidence | application runtime | no |\n| MCP transport classification of an uncertain governed failure | MCP adapter boundary | no policy authority; transport only |\n| orchestration mechanics | framework adapter | yes |",
    "architecture authority table",
)

replace_once(
    "docs/ARCHITECTURE.md",
    "When policy returns `require_human_approval`, approval is resolved from a separate `ActionApprovalProvider`. Trusted `HumanApprovalEvidence` must match the exact proposal and caller context before execution can proceed.\n\nThe resulting `ActionExecutionEvidence` records authorization, approval, and execution as independent facts. This preserves another important distinction:",
    "When policy returns `require_human_approval`, approval is resolved from a separate `ActionApprovalProvider`. Trusted `HumanApprovalEvidence` must match the exact proposal and caller context before execution can proceed. The controlled provider treats approval as bounded authority: evidence is timezone-aware, exact-scope, single-use, revocable before claim, source-isolated, and evaluated against an application-owned trusted clock.\n\nA separate `ActionApproverAuthorizer` verifies whether the trusted `approver_id` may approve the exact `(approver_id, caller_id, identity_source, action, resource, environment)` scope. Human approval therefore does not imply global reviewer authority.\n\nFor authenticated composition, `AuthenticatedGovernedActionRuntime` first establishes trusted caller context through a framework-neutral authenticator and only then delegates to the same governed authorization/approval/execution runtime. Rejected authentication never reaches mutable authorization or execution, and raw credentials are not copied into `ActionContext` or execution evidence.\n\nThe resulting `ActionExecutionEvidence` records authorization, approval lifecycle, approver authorization, and execution as independent facts. This preserves another important distinction:",
    "architecture approval and authentication runtime",
)

replace_once(
    "docs/ARCHITECTURE.md",
    "The controlled in-memory finding acknowledgement adapter is mutable enough to prove state change without introducing external side effects. It validates its concrete operation/resource invariants but never owns authorization.\n\nSee [Governed Agent Actions](security/GOVERNED_AGENT_ACTIONS.md) for the full trust model, adversarial cases, conformance matrix, and explicit non-goals.",
    "If an authorized executor raises after invocation, `GovernedActionRuntime` raises `GovernedActionExecutionError` carrying immutable `ActionExecutionFailureEvidence`. That evidence preserves the exact authority chain, sets `execution_attempted=true`, `failure_reason=executor_error`, and `external_side_effect_state=unknown`, and excludes raw executor text. The original exception remains only as the local chained Python cause. Authenticated composition re-wraps this state as `AuthenticatedGovernedActionExecutionError` while preserving the successful authentication evidence and base-error compatibility.\n\nA failed HITL execution does not restore already-claimed approval authority. The lab deliberately does not infer rollback, idempotency, compensation, or transactional external state from a raised exception.\n\nThe controlled in-memory finding acknowledgement adapter is mutable enough to prove state change without introducing external side effects. It validates its concrete operation/resource invariants but never owns authorization.\n\nSee [Governed Agent Actions](security/GOVERNED_AGENT_ACTIONS.md) for the full trust model, adversarial cases, conformance matrix, and explicit non-goals.",
    "architecture failure evidence",
)

replace_once(
    "docs/ARCHITECTURE.md",
    "The governed mutable-action Step also uses `max_retries=0`. A regression test proves a failing mutable executor is invoked exactly once so framework retry cannot silently multiply side effects.",
    "The governed mutable-action Step also uses `max_retries=0`. A regression test proves a failing mutable executor is invoked exactly once so framework retry cannot silently multiply side effects. Because Agno represents the workflow failure as `RunStatus.error`, the adapter also preserves and re-raises the original application-owned `GovernedActionExecutionError` instead of replacing it with a generic framework error.",
    "architecture Agno hardening",
)

replace_once(
    "docs/ARCHITECTURE.md",
    "The suite covers exact allow, explicit deny, missing HITL approval, validated trusted approval, caller mismatch, identity-source mismatch, and resource escalation.\n\nEach adapter must match the direct application baseline for:\n\n- complete `ActionExecutionEvidence`;\n- observable in-memory mutation;\n- successful execution count.",
    "The suite covers exact allow, explicit deny, missing and validated HITL approval, unauthorized approver, expired/revoked approval, caller mismatch, identity-source mismatch, resource escalation, and an authorized executor-failure path.\n\nEach adapter must match the direct application baseline for:\n\n- complete `ActionExecutionEvidence` on success/pre-executor paths;\n- complete `ActionExecutionFailureEvidence` on the post-executor failure path;\n- observable in-memory mutation;\n- successful execution or executor-attempt count, as applicable;\n- raw executor text exclusion from structured evidence and governed error text.",
    "architecture cross-framework conformance",
)

replace_once(
    "docs/ARCHITECTURE.md",
    "For governed mutable actions, `ActionExecutionEvidence` is currently the application evidence contract. Production audit storage and correlation infrastructure are outside the current lab scope.",
    "For governed mutable actions, the application evidence contracts include successful execution, typed governed executor failure, authenticated execution, and authenticated governed failure evidence. Production audit persistence, cryptographic signing, tamper-proof storage, and cross-system transaction proof remain outside the current lab scope.",
    "architecture telemetry evidence",
)

replace_once(
    "docs/ARCHITECTURE.md",
    "The project keeps read-only applicability and governed mutable actions in separate local MCP servers.\n\nFor the mutable server:\n\n- the MCP tool is available to the host, but availability does not imply authorization;\n- the action name is fixed by the handler rather than accepted as arbitrary model input;\n- `resource` and `environment` remain untrusted tool arguments;\n- the controlled caller context is created by server composition code;\n- the tool schema does not accept caller identity or approval identifiers;\n- application policy/runtime still owns the authorization and execution boundary;\n- a separate read-only state tool verifies the real in-memory side effect independently from returned execution evidence.\n\nThe current `local-mcp-host` caller is a local deployment-scoped trust context for the experiment. It is not authenticated end-user identity.",
    "The project keeps read-only applicability and governed mutable actions in separate checked-in local MCP servers. A third authenticated governed-action server is intentionally used only by isolated compatibility/STDIO tests because its synthetic credential material belongs to the trusted host/process environment rather than project configuration.\n\nFor mutable servers:\n\n- MCP Tool availability does not imply authorization or execution;\n- the action name is fixed by the handler rather than accepted as arbitrary model input;\n- `resource` and `environment` remain untrusted tool arguments;\n- trusted-composition caller context or successful host-injected authentication establishes `ActionContext` outside the Tool schema;\n- the Tool schema does not accept caller identity, raw credential, identity source, approval identifiers, or approver identity;\n- application policy/runtime still owns authorization, approval, approver authorization, and execution;\n- a separate read-only state Tool verifies the controlled in-memory side effect independently from returned execution evidence;\n- post-executor `GovernedActionExecutionError` / `AuthenticatedGovernedActionExecutionError` states are mapped to host-visible `MCPError` protocol failures with safe evidence rather than ordinary model-correctable Tool errors.\n\nThe protocol-error mapping is a transport classification, not a new policy engine and not a universal no-retry guarantee: a host can still retry programmatically. `external_side_effect_state=unknown` remains unchanged even when the controlled fixture observes zero mutation. The `local-mcp-host` caller is a local deployment-scoped trust context; the authenticated experiment demonstrates host-injected service authentication, not remote transport-bound end-user identity.",
    "architecture MCP boundary",
)

# docs/MCP.md
replace_once(
    "docs/MCP.md",
    "The source-aware policy for this experiment binds authority to `identity_source = api_key`. Real\nSTDIO subprocess checks prove that missing credentials fail closed, invalid credentials return\nrejection evidence with zero mutation, and valid authentication can still be denied, require human\napproval, or execute depending on the exact action scope. A separate read-only state Tool verifies\nside effects independently. Smoke credentials are generated at runtime and no expected plaintext API\nkey is committed.",
    "The source-aware policy for this experiment binds authority to `identity_source = api_key`. Real\nSTDIO subprocess checks prove that missing credentials fail closed, invalid credentials return\nrejection evidence with zero mutation, and valid authentication can still be denied, require human\napproval, execute, or reach a typed governed executor-failure path depending on the exact action\nscope. Successful authentication evidence remains distinct from authorization/execution evidence, and\nraw credentials are excluded from structured failure evidence. A separate read-only state Tool verifies\nside effects independently. Smoke credentials are generated at runtime and no expected plaintext API\nkey is committed.",
    "MCP authenticated current behavior",
)

replace_once(
    "docs/MCP.md",
    "This is provider-free local host-injection evidence. It does **not** establish remote MCP identity,\ntransport-bound authentication, OAuth/OIDC/JWT/mTLS, production secret storage, rotation, expiry, or\nend-user identity.\n\n## Governance",
    "This is provider-free local host-injection evidence. It does **not** establish remote MCP identity,\ntransport-bound authentication, OAuth/OIDC/JWT/mTLS, production secret storage, rotation, expiry, or\nend-user identity.\n\n### Uncertain post-executor failure boundary\n\nThe mutable MCP experiments distinguish a pre-executor Tool failure from a failure that occurs after\n`GovernedActionRuntime` has already invoked a mutable executor. In the latter case the application\nreports `external_side_effect_state = unknown`; returning that state as an ordinary model-visible Tool\nerror would create a natural self-directed retry channel even though a previous side effect may have\ncommitted.\n\nThe trusted-composition server therefore catches only `GovernedActionExecutionError`, and the\nauthenticated server catches only `AuthenticatedGovernedActionExecutionError`. Each is translated to\na host-visible `MCPError` protocol failure with generic message text and safe structured failure\nevidence in protocol data. Raw executor text and raw credentials are not copied into the protocol\npayload.\n\nThe exact MCP 2.1.1 compatibility and real STDIO smokes require this failure to raise as a protocol\nerror rather than `CallToolResult(is_error=true)`. Controlled fixtures may observe zero mutation for\nthe synthetic failing resource, but that observation never rewrites the application fact that the\nexternal side-effect state is `unknown`.\n\nThis is a transport classification, not a universal no-retry mechanism. A host can still implement\nprogrammatic retry, and the lab does not claim idempotency, rollback, compensation, two-phase commit,\nor transactional coupling to an external system.\n\n## Governance",
    "MCP uncertain execution section",
)

# docs/DEVELOPMENT.md
replace_once(
    "docs/DEVELOPMENT.md",
    "When changing retry or timeout behavior, document the ownership boundary and add a regression test for the configured policy.\n\n## Provider-backed development",
    "When changing retry or timeout behavior, document the ownership boundary and add a regression test for the configured policy.\n\n## Mutable execution failure ownership\n\nFor governed mutable actions, a raised executor exception is not equivalent to a clean non-execution. Once the executor boundary has been crossed, preserve the application-owned `GovernedActionExecutionError` / `ActionExecutionFailureEvidence` contract instead of converting it to a generic framework error.\n\nRequired invariants for this path:\n\n- exactly one executor attempt unless a separate, explicitly designed retry/idempotency contract exists;\n- `execution_attempted=true`;\n- `failure_reason=executor_error`;\n- `external_side_effect_state=unknown`;\n- raw executor text remains outside structured evidence and governed error text;\n- the original exception may remain only as the local Python `__cause__`;\n- a claimed HITL approval is not silently restored after a failed executor attempt;\n- framework status/error wrappers must not erase the application failure provenance.\n\nAt MCP boundaries, do not turn an uncertain post-executor governed failure into an ordinary model-correctable Tool error. The current local experiment maps only the typed governed failure class to a protocol `MCPError`; that transport behavior is not a substitute for idempotency or a host-level retry policy.\n\n## Provider-backed development",
    "development mutable failure ownership",
)

replace_once(
    "docs/DEVELOPMENT.md",
    "When changing MCP behavior:\n\n- preserve the application ports;\n- keep authorization/least-privilege decisions explicit;\n- run the MCP compatibility and real STDIO smoke gates;\n- verify current MCP documentation/spec behavior before using new APIs.",
    "When changing MCP behavior:\n\n- preserve the application ports;\n- keep authentication, trusted context, authorization, approval and approver authorization as separate concerns;\n- preserve typed governed failure evidence and the `external_side_effect_state=unknown` contract after executor invocation;\n- do not expose raw credentials or raw executor errors through Tool schemas/results/protocol data;\n- preserve the distinction between model-visible Tool errors and host-visible protocol errors for uncertain mutable execution;\n- run the MCP compatibility and real STDIO smoke gates;\n- verify current MCP documentation/spec behavior before using new APIs.",
    "development MCP checklist",
)

replace_once(
    "docs/DEVELOPMENT.md",
    "- Did a framework abstraction accidentally take ownership of domain/security policy?\n- Are retries, fallbacks, timeouts, or model-call accounting still explicit?",
    "- Did a framework abstraction accidentally take ownership of domain/security policy?\n- Did a framework/transport error path erase authentication, authorization, approval or executor-failure provenance?\n- Are retries, fallbacks, timeouts, mutable executor attempts, or model-call accounting still explicit?",
    "development PR checklist",
)

# docs/AGENTIC_FAST_TRACK.md
replace_once(
    "docs/AGENTIC_FAST_TRACK.md",
    "### CrewAI, LlamaIndex, and Agno\n\nImplement the same workload through alternative framework adapters.\n\n## Development sequence",
    "### CrewAI, LlamaIndex, and Agno\n\nImplement the same workload through alternative framework adapters.\n\n## Current implemented state\n\nThe original comparison roadmap is complete and the lab now also includes:\n\n* a governed LiteLLM provider boundary plus persisted five-way provider-backed evaluation evidence;\n* read-only and mutable MCP v2 STDIO experiments;\n* application-owned exact source-aware mutable-action authorization;\n* service-caller authentication separated from authorization;\n* bounded, single-use, revocable and time-limited human approval;\n* independent approver authorization;\n* governed success and executor-failure evidence, including authenticated composition;\n* fail-closed MCP protocol classification for uncertain post-executor failures;\n* LangGraph, CrewAI Flow, LlamaIndex and Agno governed-action conformance against the direct application runtime;\n* Agno mutable Step retry suppression and governed failure-provenance preservation;\n* provider-free quality, security, MCP and OpenTelemetry CI gates.\n\nThe latest published milestone is v1.3.0; some failure-provenance and MCP hardening exists only on current `main` until a later release is explicitly published.\n\n## Development sequence",
    "fast track current state",
)

replace_once(
    "docs/AGENTIC_FAST_TRACK.md",
    "shared contracts\n    ↓\ndeterministic fixtures\n    ↓\nLangChain tools\n    ↓\nLangGraph v1\n    ↓\nLLM structured reasoning\n    ↓\ntool calling\n    ↓\nrouting and failure handling\n    ↓\nevaluations\n    ↓\nCrewAI\n    ↓\nLlamaIndex\n    ↓\nAgno\n    ↓\ncross-framework benchmark\n    ↓\nMCP / observability / HITL / security",
    "shared contracts\n    ↓\ndeterministic fixtures and validation\n    ↓\nLangGraph / CrewAI / LlamaIndex / Agno implementations\n    ↓\ncross-framework evaluation and immutable evidence\n    ↓\nLiteLLM provider boundary\n    ↓\nMCP / OpenTelemetry / adversarial security\n    ↓\ngoverned mutable actions\n    ↓\ntrusted caller identity and source-aware authorization\n    ↓\nhuman approval lifecycle and approver authorization\n    ↓\nexecutor-failure provenance and uncertain-execution hardening\n    ↓\ncross-framework governed failure conformance",
    "fast track sequence",
)

# docs/FRAMEWORK_DECISION_MATRIX.md
replace_once(
    "docs/FRAMEWORK_DECISION_MATRIX.md",
    "The earlier provider-direct five-way artifacts remain valid historical evidence. This matrix uses the immutable Phase 15 final-evaluation bundle as the current-state source instead of rewriting those historical artifacts.",
    "The earlier provider-direct five-way artifacts remain valid historical evidence. This matrix uses the immutable Phase 15 final-evaluation bundle as the current analysis-workload source instead of rewriting those historical artifacts. Separately, provider-free governed-action conformance now exercises authorization, HITL/approver states and executor-failure provenance across LangGraph, CrewAI Flow, LlamaIndex and Agno; those security results inform the qualitative sections below but do not alter the immutable v1.0 benchmark metrics.",
    "framework matrix evidence scope",
)

replace_once(
    "docs/FRAMEWORK_DECISION_MATRIX.md",
    "Agno `Step` retries require an explicit `max_retries=0` override for benchmark-sensitive steps so framework retries cannot occur outside the application-governed evaluator loop. Vendor telemetry is also explicitly disabled for the benchmark runtime.",
    "Agno `Step` retries require an explicit `max_retries=0` override for benchmark-sensitive and mutable governed steps so framework retries cannot occur outside application-owned control. Vendor telemetry is also explicitly disabled for the benchmark runtime. For the governed mutable path, the adapter additionally preserves and re-raises the original `GovernedActionExecutionError` when Agno reports `RunStatus.error`, preventing framework status from erasing application-owned failure evidence.",
    "framework matrix Agno security",
)

replace_once(
    "docs/FRAMEWORK_DECISION_MATRIX.md",
    "All five variants in this lab were deliberately engineered to answer those questions through shared application-owned controls and the same governed gateway alias.\n\n## Practical selection guide",
    "All five analysis variants in this lab were deliberately engineered to answer those questions through shared application-owned controls and the same governed gateway alias. The four governed mutable-action adapters additionally match the direct application runtime for exact allow/deny/HITL states, approver authorization failures, identity/source mismatches, scope escalation and authorized executor failure.\n\nThat second conformance surface changes the framework-security question from merely \"can this framework call a tool?\" to \"can this framework preserve application-owned authority and failure provenance without adding an unsafe retry or generic error wrapper?\" Current provider-free tests say yes for LangGraph, CrewAI Flow, LlamaIndex and Agno under the controlled workload.\n\n## Practical selection guide",
    "framework matrix security interpretation",
)

replace_once(
    "docs/FRAMEWORK_DECISION_MATRIX.md",
    "The decision matrix should be revisited when the lab adds or materially expands:\n\n- tool calls and MCP authorization beyond compatibility smoke;\n- multi-agent delegation;\n- memory and persistence;\n- richer prompt-injection scenarios;\n- human approval steps;\n- provider/model variation behind the gateway;\n- larger latency samples and uncertainty estimates;\n- deployment-grade tracing/exporter composition.",
    "The decision matrix should be revisited when the lab adds or materially expands:\n\n- remote/transport-bound MCP authentication and authorization instead of local host composition;\n- real external mutable systems where idempotency, rollback or compensation become concrete requirements;\n- durable/distributed or multi-party approval infrastructure;\n- multi-agent delegation;\n- framework-native memory, checkpointing and persistence in the comparable workload;\n- richer prompt-injection and tool-abuse scenarios;\n- provider/model variation behind the gateway;\n- larger latency samples and uncertainty estimates;\n- deployment-grade tracing/exporter composition.",
    "framework matrix future changes",
)

replace_once(
    "docs/FRAMEWORK_DECISION_MATRIX.md",
    "Architecture and authority boundaries:\n\n- [`ARCHITECTURE.md`](ARCHITECTURE.md)\n- [LiteLLM gateway foundation](litellm/GATEWAY_FOUNDATION.md)",
    "Architecture, authority and governed-action conformance:\n\n- [`ARCHITECTURE.md`](ARCHITECTURE.md)\n- [Governed Agent Actions](security/GOVERNED_AGENT_ACTIONS.md)\n- [cross-framework governed-action conformance](../tests/integration/test_governed_action_framework_conformance.py)\n- [LiteLLM gateway foundation](litellm/GATEWAY_FOUNDATION.md)",
    "framework matrix evidence links",
)
