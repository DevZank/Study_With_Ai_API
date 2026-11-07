# Planejamento de Construção — Plataforma de Estudos com IA

> **Versão:** 1.0 — 06/11/2026  
> **Status:** Especificação para implementação incremental  
> **Idioma do produto e comentários de código:** Português brasileiro (pt-BR)  
> **Estratégia:** Local-first, extensível para produto comercial

## 1. Visão do produto

Construir uma aplicação web executada localmente que transforme qualquer tema em uma experiência de aprendizagem organizada, didática, adaptativa e gamificada. O produto combina conversa com IA, trilhas personalizadas, quatro modos pedagógicos, caderno livre e acompanhamento de aprendizagem. Deve funcionar com Ollama em GPUs de **6 GB de VRAM** mediante escolha adequada de modelo e configuração, e permitir modelos externos mediante chave de API.

**Não é apenas um chatbot.** A lógica de trilhas, revisões, avaliações, progresso, anotações e persistência é responsabilidade da aplicação; o modelo de IA gera e adapta conteúdos sob contratos validados.

### 1.1 Princípios inegociáveis
1. Usuário decide o que estudar e quando avançar; IA sugere, não impõe.
2. Geração incremental: planejar trilha sem gerar todo seu conteúdo; produzir módulo/aula quando solicitado.
3. Local-first: dados persistidos localmente; uso de internet e APIs externas claramente identificado.
4. **Pesquisa na internet somente com autorização explícita**, específica e revogável antes da operação.
5. Modelos pequenos são cidadãos de primeira classe: respostas curtas, contexto controlado, validação, retry limitado e fallback.
6. Interface pedagógica estruturada, acessível, com baixa sobrecarga cognitiva.
7. Métricas de domínio e retenção são estimativas, não provas absolutas de aprendizado.
8. Arquitetura modular preparada para distribuição comercial sem adicionar complexidade prematura.

## 2. Escopo funcional completo

### F01 — Temas e navegação [ESSENCIAL / MVP]
- Criar, renomear, arquivar, excluir e pesquisar temas; listar recentes na barra lateral semelhante ao histórico de chats.
- Histórico de sessões e mensagens persistido; continuidade por tema.
- Um tema pode conter conversas livres, uma ou mais trilhas, cadernos e materiais.
- Exclusão com confirmação, política de recuperação e limpeza de arquivos associados.

### F02 — Quatro modos pedagógicos [ESSENCIAL / MVP]
- **Estudar:** aprofundamento progressivo, fundamentos, contexto histórico quando pertinente, relações entre conceitos, curiosidades úteis, exemplos e checkpoints.
- **Memorizar:** flashcards, recuperação ativa, lacunas, associação, vocabulário, traduções, revisões espaçadas (FSRS).
- **Aprender:** explicação direta e breve, analogias úteis, exemplos e aprofundamento sob demanda.
- **Praticar:** múltipla escolha, aberto, verdadeiro/falso, lacunas, identificação de erros, desafios e exercícios de programação. Dicas progressivas e feedback antes da solução quando adequado.
- Modos compartilham tema, objetivos, progresso e contexto resumido; alternância não perde histórico.

### F03 — Trilhas guiadas [ESSENCIAL / MVP]
- Usuário informa objetivo, experiência prévia, disponibilidade opcional e preferência de profundidade.
- IA propõe apenas **esqueleto**: título, objetivo, pré-requisitos, módulos, objetivos e critérios de conclusão.
- Usuário aceita, edita, remove, adiciona e reordena módulos; navegação não é bloqueada.
- Ao abrir um módulo, backend escolhe granularidade (módulo inteiro ou aulas menores) conforme tamanho, complexidade e orçamento de contexto; não gera módulos futuros.
- Cada unidade gerada possui objetivos, blocos de conteúdo, exercícios e referências quando existentes.
- Resumo de conclusão estruturado registra conceitos, erros, domínio estimado e próximos passos; substitui histórico integral no contexto posterior.
- Cache, versionamento e regeneração explícita; alteração de planejamento não destrói anotações/progresso sem confirmação.

### F04 — Caderno integrado e livre [ESSENCIAL para produto / MVP em etapas]
- **Caderno global e cadernos por tema/trilha integrados**; páginas podem ser relacionadas a vários temas sem duplicação.
- Pastas, páginas, tags, links internos, busca, editor rico, listas, tabelas, blocos de código, fórmulas, imagens e anexos.
- Selecionar trecho de qualquer resposta da IA → ação contextual **“Salvar no caderno”** → escolher página ou criar uma; preservar origem (tema, mensagem, data, intervalo selecionado) e permitir editar a cópia.
- **Desenho livre:** pincel, caneta, borracha, formas, setas, texto, cores, zoom/pan, seleção, mover/redimensionar, desfazer/refazer; idealmente canvas infinito com inserção de imagens e links para notas.
- Estratégia recomendada: TipTap para documentos e tldraw ou Excalidraw embutido para quadros; validar licença e viabilidade comercial antes da escolha final.
- Autosave, recuperação de rascunhos, exportação, importação e versionamento básico; não sobrescrever conteúdo autoral por ação da IA.
- Transformar notas em flashcards/exercícios **somente sob comando**; IA pode consultar notas selecionadas com consentimento contextual.

### F05 — Motor pedagógico e progresso [ESSENCIAL / MVP progressivo]
- Diagnóstico inicial opcional; objetivos, pré-requisitos e mapa de conceitos.
- Três indicadores separados: conclusão (atividades), domínio estimado (desempenho) e retenção estimada (revisões).
- Revisão espaçada FSRS, agenda de cartões, estatísticas e registro de tentativas.
- Recomendações adaptativas: revisar erro recorrente, avançar quando demonstra domínio, ajustar dificuldade.
- Recompensar compreensão e consistência, não quantidade de mensagens.

### F06 — Gamificação leve [IMPORTANTE]
- XP, níveis, conquistas e progresso por trilha; metas opcionais.
- Regras determinísticas, anti-farming, sem penalização excessiva por pausa.
- Preferência para reduzir ou ocultar elementos de gamificação.

### F07 — Experiência acessível e envolvente [ESSENCIAL]
- Blocos curtos, uma etapa por vez, checkpoints, exemplos concretos e variação de formato.
- Modo foco, controle de profundidade, ritmo, tamanho de sessão, pausas opcionais.
- Navegação por teclado, contraste, rótulos, leitor de tela, movimento reduzido e estados de carregamento claros.
- Não prometer tratamento de TDAH; oferecer opções flexíveis para diferentes necessidades de atenção.

### F08 — IA local e provedores externos [ESSENCIAL / MVP local; externos na fase seguinte]
- Ollama: listar modelos instalados, verificar serviço, selecionar, transmitir tokens, cancelar geração, ajustar contexto.
- OpenAI, Gemini e adaptadores futuros; chave de API configurável; teste de conexão; custos estimados quando disponíveis.
- **Seleção automática com override manual**: roteamento por tarefa, capacidade declarada, privacidade, custo e disponibilidade; nunca mudar para nuvem silenciosamente.
- Perfis econômico/equilibrado/qualidade; fallback controlado; CPU opcional.
- Em 6 GB de VRAM, qualidade/velocidade variam conforme modelo, quantização, contexto e hardware; benchmark antes de anunciar compatibilidade.
- Guardar credenciais criptografadas, preferencialmente protegidas por armazenamento seguro do SO; não enviá-las ao frontend após cadastro.

### F09 — Materiais, RAG e pesquisa [IMPORTANTE]
- Importar PDFs, textos e documentos suportados; extrair, segmentar, indexar, pesquisar e citar trechos.
- Busca lexical SQLite FTS5 e embeddings locais/índice vetorial quando úteis.
- Links e pesquisa web apenas após **pedido de autorização** mostrando finalidade e o que será consultado; negativa não impede continuar sem web.
- Exibir proveniência; nunca inventar fonte; distinguir conhecimento interno, arquivo local e pesquisa autorizada.
- Proteger contra prompt injection em documentos e páginas.

### F10 — Respostas estruturadas [ESSENCIAL / MVP]
- Backend recebe JSON de blocos validados por Pydantic; frontend renderiza por whitelist de componentes.
- Tipos: texto, explicação, exemplo, código, fórmula, tabela, comparação, flashcard, quiz, exercício, dica, resumo, timeline, diagrama, curiosidade e fonte.
- Não renderizar HTML/JS arbitrário do modelo; sanitização e limites de tamanho.
- Retry limitado de JSON inválido, correção estruturada e fallback textual seguro.

### F11 — Administração local e confiabilidade [ESSENCIAL]
- Configurações, exportar/importar dados, backup/restauração, migrações, logs sem dados sensíveis.
- Tratamento de indisponibilidade de Ollama, API, internet, cancelamento e interrupções; autosave.
- Diagnóstico de ambiente e requisitos de hardware.

### F12 — Evolução comercial [PREPARAÇÃO AGORA; IMPLEMENTAÇÃO FUTURA]
- Isolar perfil/usuário em todas as entidades; autenticação, licenciamento, cobrança e sincronização apenas quando definidos.
- Separar dados locais de serviços futuros; estudar termos e licenças de bibliotecas/modelos antes de distribuição.
- Planejar atualização do app, suporte, telemetria opcional e privacidade/LGPD; nunca coletar dados de estudo sem consentimento.

## 3. Stack proposta

| Camada | Escolha | Observações |
|---|---|---|
| Frontend | React + TypeScript + Vite | SPA local, componentes tipados |
| UI | Tailwind CSS + componentes acessíveis | Tema claro/escuro, responsivo |
| Estado/dados | TanStack Query + estado local mínimo | Evitar duplicar cache de servidor |
| Backend | Python + FastAPI + Pydantic | API REST + streaming SSE |
| Persistência | SQLite + SQLAlchemy + Alembic | WAL e backups consistentes |
| IA local | Ollama | HTTP local, modelos configuráveis |
| Provedores cloud | Adaptadores OpenAI/Gemini | Sem SDK espalhado no domínio |
| Editor de notas | TipTap | Rich text serializado e versionado |
| Quadro de desenho | tldraw ou Excalidraw (avaliar) | Verificar licença comercial |
| Busca | SQLite FTS5 | Vetorial opcional por interface |
| Fórmulas/código | KaTeX + Shiki | Renderização segura |
| Revisão | FSRS | Testes determinísticos |
| Testes | Pytest, Vitest, Playwright | E2E e mocks de IA |

## 4. Arquitetura e responsabilidades

```text
[Browser: React]
    | REST / SSE
[FastAPI: controllers + schemas]
    | application services / use cases
    +-- ThemeService / ConversationService
    +-- TrailPlanner / LessonGenerator
    +-- LearningEngine / AssessmentService / ReviewScheduler
    +-- NotebookService / MaterialService / SearchService
    +-- ModelRouter / GenerationService / ConsentService
    | interfaces (ports)
    +-- SQLite repositories
    +-- Ollama adapter
    +-- OpenAI/Gemini adapters
    +-- File extraction / indexing / authorized web search
```

**Separação:** regras de negócio e agendamento de revisão não dependem de LLM; LLM não escreve diretamente no banco; controllers não contêm lógica pedagógica; frontend não guarda segredos. Operações longas têm status, cancelamento e idempotência.

### 4.1 Estrutura de diretórios

Dois repositórios independentes, sem dependência de arquivos da pasta pai:

```text
Frontend/
├── AGENTS.md, TASKS.md, PLANEJAMENTO_PLATAFORMA_ESTUDOS_IA.md
├── README.md, package.json, package-lock.json
├── .github/workflows/
├── docs/{product,architecture,api,development}/
├── src/{app,pages,features,components,lib,hooks,types,styles}/
└── tests/

Backend/
├── AGENTS.md, TASKS.md, PLANEJAMENTO_PLATAFORMA_ESTUDOS_IA.md
├── README.md, pyproject.toml, requirements.lock
├── .github/workflows/
├── docs/{product,architecture,api,development}/
├── scripts/
├── src/study_api/{core,presentation,application,domain,infrastructure,workers}/
└── tests/
```

A estrutura inclui diretórios previstos para expansão; não exige criar módulos vazios. O contrato HTTP fica em docs/api/contracts.md de cada repositório. O acompanhamento integrado tem referência principal em Backend/TASKS.md; a cópia do frontend deve registrar quando precisa ser conciliada. Cada README contém comandos executados na raiz do próprio repositório.
**Convenções:** nomes de código, diretórios e endpoints em inglês por interoperabilidade; textos de interface, documentação voltada ao usuário, comentários e docstrings em pt-BR. Nunca comentar o óbvio; comentar intenção, invariantes, decisões e trade-offs.

## 5. Modelo de dados (entidades principais)

Todas as entidades possuem `id` UUID, `created_at`, `updated_at` quando aplicável; relações, índices, constraints e regras de deleção devem ser definidos nas migrações. Incluir `owner_id` ou `profile_id` desde o início para migração multiusuário futura, mesmo com um perfil local padrão.

| Entidade | Campos principais | Relações / observações |
|---|---|---|
| `profiles` | id, display_name, preferences_json | Perfil local inicial |
| `topics` | owner_id, title, description, status | Agrupa conversas, trilhas e notas |
| `conversations` | topic_id, title, active_mode | Uma ou várias por tema |
| `messages` | conversation_id, role, content, model_id, status, token_usage | Mensagens e metadados; ordenação estável |
| `learning_goals` | topic_id, objective, prior_level, preferences_json | Objetivo explícito |
| `trails` | topic_id, goal_id, title, status, plan_version | Planejamento editável |
| `trail_modules` | trail_id, position, title, objectives_json, prerequisites_json, status | Conteúdo lazy |
| `lessons` | module_id, position, content_version, status, content_json | Unidades geradas sob demanda |
| `concepts` | topic_id, name, definition, metadata_json | Conhecimento rastreável |
| `concept_dependencies` | concept_id, prerequisite_id | Grafo de pré-requisitos |
| `lesson_concepts` | lesson_id, concept_id | N:N |
| `exercises` | lesson_id, type, prompt_json, answer_key_json, difficulty | Gabarito restrito ao backend |
| `exercise_attempts` | exercise_id, profile_id, response_json, grade, feedback_json | Histórico de tentativas |
| `concept_mastery` | profile_id, concept_id, score, evidence_count, last_assessed_at | Estimativa e evidências |
| `flashcards` | topic_id, concept_id, front_json, back_json, source_ref | Conteúdo de memorização |
| `review_states` | profile_id, flashcard_id, due_at, stability, difficulty, reps, lapses | Estado FSRS |
| `review_events` | review_state_id, rating, reviewed_at, elapsed_days | Histórico imutável |
| `notebooks` | owner_id, scope_type, scope_id, title | Global ou por tema/trilha |
| `notebook_folders` | notebook_id, parent_id, title, position | Hierarquia |
| `notebook_pages` | notebook_id, folder_id, title, content_json, version | Rich text e metadados |
| `drawing_boards` | page_id, scene_json, scene_version, preview_asset_id | Desenho editável |
| `saved_clippings` | page_id, message_id, selected_text, source_range_json | Origem rastreável |
| `assets` | owner_id, filename, mime, path, size, checksum | Arquivos locais |
| `materials` | topic_id, asset_id, source_type, title, status | PDF, documento, URL autorizada |
| `material_chunks` | material_id, position, text, source_locator_json | RAG e citações |
| `ai_providers` | owner_id, provider_type, config_json, secret_ref, enabled | Sem chaves em plaintext |
| `ai_models` | provider_id, model_name, capabilities_json, limits_json | Modelos disponíveis |
| `generation_jobs` | owner_id, task_type, status, model_id, request_hash, error_code | Idempotência, cancelamento |
| `web_consents` | owner_id, scope, purpose, query_preview, granted_at, expires_at | Autorização auditável |
| `xp_events` | owner_id, source_type, source_id, points | Ledger anti-duplicação |
| `achievements` | code, title, rule_json | Definições |
| `earned_achievements` | owner_id, achievement_id, earned_at | Conquistas |

**Regras de integridade:** `UNIQUE(profile_id, concept_id)` em domínio; `UNIQUE(profile_id, flashcard_id)` em revisão; índices por `due_at`, `topic_id`, `trail_id`, `conversation_id`; IDs de assets não devem aceitar path arbitrário do cliente. Gabaritos não são retornados antes da tentativa ou revelação permitida.

## 6. Contratos de API (versão `/api/v1`)

Formato de erro padronizado:

```json
{"error":{"code":"MODEL_UNAVAILABLE","message":"Modelo indisponível.","details":{},"request_id":"uuid"}}
```

Paginação via `limit` e cursor; validação de payload, ownership, limites de tamanho e status HTTP coerentes. Exemplos de endpoints:

| Método | Endpoint | Responsabilidade |
|---|---|---|
| GET/POST | `/topics` | Listar/criar temas |
| GET/PATCH/DELETE | `/topics/{topic_id}` | Detalhes, edição, exclusão |
| GET/POST | `/topics/{topic_id}/conversations` | Conversas |
| GET | `/conversations/{id}/messages` | Histórico paginado |
| POST | `/conversations/{id}/messages` | Criar mensagem e iniciar geração |
| POST | `/trails/plan` | Criar job de planejamento da trilha |
| GET/PATCH | `/trails/{id}` | Consultar/editar trilha |
| POST | `/trails/{id}/modules` | Adicionar módulo |
| PATCH | `/trails/{id}/modules/order` | Reordenar módulos |
| POST | `/modules/{id}/generate` | Gerar conteúdo incremental (job) |
| GET | `/modules/{id}/lessons` | Listar aulas geradas |
| POST | `/exercises/{id}/attempts` | Responder e corrigir exercício |
| GET | `/reviews/due` | Revisões pendentes |
| POST | `/reviews/{flashcard_id}/grade` | Registrar revisão FSRS |
| GET/POST | `/notebooks` | Listar/criar cadernos |
| GET/POST | `/notebooks/{id}/pages` | Páginas |
| GET/PATCH | `/pages/{id}` | Ler/salvar documento com controle de versão |
| GET/PUT | `/pages/{id}/drawing` | Ler/salvar cena de desenho |
| POST | `/pages/{id}/clippings` | Salvar seleção de resposta |
| POST | `/materials` | Upload controlado |
| GET | `/materials/{id}/status` | Estado da extração/indexação |
| GET | `/ai/providers` | Provedores configurados, sem segredos |
| POST | `/ai/providers` | Adicionar provedor e armazenar segredo |
| POST | `/ai/providers/{id}/test` | Teste de conexão |
| GET | `/ai/models` | Modelos disponíveis/capacidades |
| GET | `/jobs/{id}` | Estado de geração |
| GET | `/jobs/{id}/events` | Streaming SSE |
| POST | `/jobs/{id}/cancel` | Cancelar geração |
| POST | `/web-search/consent-requests` | Preparar solicitação de autorização |
| POST | `/web-search/consent-requests/{id}/decision` | Aprovar/negar |
| POST | `/web-search` | Pesquisar apenas com autorização válida |
| GET | `/progress/topics/{id}` | Progresso, domínio e retenção |
| POST | `/backups` | Backup consistente |

### 6.1 Exemplos de contratos

**Planejar trilha:**

```json
POST /api/v1/trails/plan
{
  "topic_id": "uuid",
  "objective": "Aprender Python para automações",
  "prior_knowledge": "iniciante",
  "preferences": {"depth": "balanced", "session_minutes": 20},
  "model_selection": {"mode": "auto"}
}
```

Resposta: `202 Accepted` com `{ "job_id": "uuid" }`; resultado final validado contém `trail`, `modules[]`, `objectives[]` e `prerequisites[]`, sem aulas completas.

**Gerar módulo:**

```json
POST /api/v1/modules/{id}/generate
{
  "granularity": "auto",
  "force_regenerate": false,
  "model_selection": {"mode": "auto"}
}
```

`granularity=auto` decide entre módulo curto e unidades menores conforme estimativa de conteúdo e capacidade do modelo; salvar resultado com versão. Requisições duplicadas retornam o mesmo job ativo quando apropriado.

**Conteúdo estruturado:**

```json
{
  "schema_version": "1.0",
  "type": "lesson",
  "title": "Variáveis em Python",
  "learning_objectives": ["Entender o que é uma variável"],
  "blocks": [
    {"id":"b1","type":"explanation","text":"Uma variável associa um nome a um valor."},
    {"id":"b2","type":"code","language":"python","code":"idade = 20"},
    {"id":"b3","type":"check_question","prompt":"Para que serve uma variável?"}
  ],
  "source_refs": []
}
```

`blocks` devem ser união discriminada por `type`; conteúdo desconhecido não executa código e é exibido em fallback seguro. `schema_version` possibilita evolução de contratos.

**SSE:** eventos `job.started`, `generation.delta`, `generation.validating`, `job.completed`, `job.failed`, `job.cancelled`, com `event_id`, `job_id` e payload; `generation.delta` é provisório, não necessariamente JSON final validado. O frontend só persiste/renderiza como conteúdo definitivo após validação.

### 6.2 Consentimento para pesquisa web
1. IA identifica necessidade de web e prepara `purpose`, consulta sugerida, dados a enviar e provedor.
2. UI apresenta pedido explícito **Permitir desta vez / Negar**.
3. Backend registra decisão, escopo e validade; pesquisa só inicia com autorização válida.
4. Recusa oferece continuação com conhecimento local ou arquivos existentes.
5. Consentimento para web **não equivale** a consentimento para enviar arquivos pessoais a APIs de IA.

## 7. Fluxos essenciais

### 7.1 Tema livre
Criar tema → selecionar modo/modelo (auto por padrão) → enviar pergunta → gerar e validar blocos → renderizar → salvar mensagem → permitir praticar, memorizar, aprofundar ou salvar seleção no caderno.

### 7.2 Trilha incremental
Objetivo → diagnóstico opcional → planejamento leve → revisão do usuário → abrir módulo → estimar granularidade → gerar unidade → validar → estudar/praticar/memorizar/tirar dúvidas → registrar evidências → concluir unidade → resumir contexto → próximo módulo somente sob demanda.

### 7.3 Caderno e desenho
Criar caderno global ou vinculado → pasta/página → editar texto rico ou abrir quadro de desenho → autosave versionado → inserir recorte de IA com proveniência → vincular a tema/trilha → exportar ou gerar revisão sob comando.

### 7.4 Roteamento automático de modelos
Classificar tarefa → filtrar modelos disponíveis por privacidade/capacidade/limites → priorizar local → estimar custo/latência → escolher → mostrar modelo efetivo → executar → fallback apenas se política do usuário permitir; nunca transmitir conteúdo à nuvem silenciosamente.

## 8. Regras de engenharia e de agentes de programação

### R01 — Não inventar e não simular
- **Nunca afirmar que implementou, testou, executou ou verificou algo sem evidência.**
- Não inventar endpoints, schemas, bibliotecas, APIs, arquivos, resultados, benchmarks ou comportamento de SDKs.
- Não criar botões decorativos, mocks ocultos, dados falsos ou fluxos que apenas parecem funcionar.
- Se uma informação crítica estiver ausente, **perguntar antes de implementar**; se não houver como verificar uma dependência, **parar a parte afetada**, explicar o bloqueio e propor opções verificáveis.
- Separar claramente fato verificado, hipótese e decisão de design.

### R02 — Trabalho incremental
- Antes de cada etapa: ler código existente, identificar dependências, escrever plano curto e critérios de aceite.
- Implementar apenas o escopo aprovado; não refatorar áreas não relacionadas sem justificativa.
- Ao concluir: executar testes disponíveis, informar comandos/resultados e pendências reais.
- Nunca avançar automaticamente para a fase seguinte quando houver decisão estrutural pendente.

### R03 — Organização e manutenção
- Respeitar fronteiras `presentation` → `application` → `domain` e adapters de `infrastructure`.
- Preferir funções pequenas, responsabilidade única, nomes descritivos e injeção de dependências.
- Não duplicar regras de negócio no frontend e backend; manter contratos versionados.
- Evitar arquivos gigantes, utilitários genéricos sem propósito e dependências circulares.
- Usar migrações de banco; nunca alterar esquema de produção manualmente.

### R04 — Idioma e comentários
- Comentários e docstrings **em pt-BR**, claros, objetivos e atualizados.
- Comentários explicam **por que** uma decisão existe, não apenas repetem o código.
- Identificadores, nomes de arquivos, endpoints e tipos podem ficar em inglês por convenção técnica.
- Textos apresentados ao usuário em pt-BR, com preparação para i18n.

### R05 — Tipagem, validação e erros
- TypeScript em modo `strict`, sem `any` injustificado.
- Python com type hints; Pydantic em todas as fronteiras de entrada/saída.
- Tratar timeout, cancelamento, retries limitados, payload malformado e falha parcial.
- Erros de domínio tipados e mensagens seguras ao usuário; logs com request IDs.
- Validar todas as respostas da IA antes de persistir como conteúdo final.

### R06 — Segurança
- Nunca commitar segredos, tokens, chaves ou dados privados de teste.
- Não usar `eval`, execução arbitrária ou HTML não sanitizado produzido pela IA.
- Se houver execução de código de exercícios, usar sandbox isolada com limites de CPU, memória, tempo, filesystem e rede; **não executar código do usuário no processo principal**.
- Restringir CORS e bind padrão a loopback; se houver acesso remoto, exigir autenticação e HTTPS.
- Uploads: tamanho, extensão/MIME, paths, limites de extração e proteção contra zip bombs.
- Não confiar em instruções embutidas em PDFs, páginas ou resultados de busca.

### R07 — Privacidade e consentimento
- Local-first por padrão; transmissão externa explícita e informada.
- Chaves de API armazenadas de modo seguro e não retornadas em respostas.
- Nunca incluir conteúdo de caderno ou arquivos em prompts externos sem política de consentimento aplicável.
- Sem telemetria por padrão; consentimento específico se introduzida futuramente.

### R08 — Confiabilidade pedagógica
- Não confundir texto fluente com conteúdo correto.
- Não inventar citações ou alegar pesquisa que não ocorreu.
- Separar gabaritos e lógica de correção da apresentação antecipada.
- Exercícios objetivos devem ter verificação determinística quando possível; questões abertas podem exigir avaliação assistida e sinalização de incerteza.
- A IA sugere revisão e avanço, mas usuário pode decidir.

### R09 — Qualidade de interface
- Estados de loading, vazio, erro, offline e sucesso em todos os fluxos.
- Design consistente, acessível e responsivo; testar teclado e foco.
- Animações discretas e respeitando `prefers-reduced-motion`.
- Componentes de conteúdo vêm de uma lista permitida, nunca de código executável enviado pelo modelo.

### R10 — Testes e documentação
- Testar regras de domínio sem IA real; usar fixtures/mocks reprodutíveis.
- Testes de integração com banco temporário e contrato de provedores.
- Testes E2E para criação de tema, trilha, geração, resposta, revisão e caderno.
- Documentar ADRs para decisões arquiteturais relevantes e manter README executável.
- Lint/format/typecheck/test devem passar antes de considerar uma tarefa concluída.

### R11 — Gestão de dependências
- Fixar versões e lockfiles; avaliar licença comercial e manutenção antes de adotar biblioteca.
- Não assumir suporte de uma API sem consultar documentação oficial ou testar integração.
- Preferir bibliotecas maduras e poucas dependências essenciais.

### R12 — Política de comunicação do agente
Ao final de cada tarefa, apresentar:
1. **Implementado:** arquivos e comportamentos reais.
2. **Verificado:** comandos e resultados efetivamente executados.
3. **Não verificado:** limitações, testes indisponíveis e hipóteses.
4. **Pendências e riscos:** problemas conhecidos.
5. **Próximo passo:** menor incremento seguro.

## 9. Plano detalhado de implementação

### Fase 0 — Fundação e validação de ambiente [BLOQUEANTE]
**Entregas:** repositório, README, setup Python/Node sem segredos, ferramentas de qualidade, convenções, ADRs iniciais, CI básico, diagnóstico de Ollama/VRAM e matriz de compatibilidade preliminar.  
**Aceite:** frontend e backend sobem localmente; healthcheck e testes básicos passam; nenhuma chave no repositório.

### Fase 1 — Temas, conversas e Ollama [MVP-1]
**Estado:** concluído e verificado em 07/11/2026; evidências e limitações no TASKS.md. Modelo local real testado, sem benchmark de 6 GB.
**Entregas:** layout com sidebar, CRUD de temas, conversas persistidas, adaptador Ollama, listagem de modelos, chat com SSE e cancelamento.  
**Aceite:** criar tema, enviar pergunta, receber resposta real do Ollama, recarregar e recuperar histórico; falha do Ollama é explicada sem perder dados.

### Fase 2 — Quatro modos e renderer estruturado [MVP-2]
**Entregas:** prompts por modo, contratos JSON, blocos visuais, validação, fallback, quizzes simples, correção e dicas.  
**Aceite:** mesmo tema suporta alternância dos quatro modos; conteúdo inválido não quebra a tela; exercício real registra tentativa.

### Fase 3 — Trilhas e geração incremental [MVP-3]
**Entregas:** wizard de objetivo, planejamento editável, reordenação de módulos, jobs de geração, granularidade automática, versões e resumo estruturado.  
**Aceite:** criar trilha de cinco módulos sem gerar aulas futuras; abrir módulo 1 gera apenas sua unidade necessária; módulo 2 permanece não gerado; recarregar preserva plano e progresso.

### Fase 4 — Caderno com texto, desenho e recortes [MVP-4]
**Entregas:** caderno global e por tema, pastas, editor rico, seleção → salvar no caderno, quadro de desenho, autosave e recuperação.  
**Aceite:** selecionar texto de resposta, salvar com origem, editar, desenhar, recarregar e recuperar texto e desenho sem perda; vínculos funcionam entre cadernos.

### Fase 5 — Memorização, revisão e progresso [MVP-5]
**Entregas:** flashcards, FSRS, fila de revisões, domínio por conceito, progresso de trilha, dashboard e XP leve.  
**Aceite:** cartões gerados e revisados persistem; vencimentos calculados de forma determinística; indicadores separados não se confundem.

### Fase 6 — Materiais e fontes [MVP-6]
**Entregas:** upload de PDF/texto, extração, busca FTS5, referências de trechos, RAG inicial, consentimento de pesquisa web e busca autorizada.  
**Aceite:** importar material, recuperar trecho relevante com referência; pesquisa não ocorre após negativa; conteúdo malicioso de documento não altera regras do sistema.

### Fase 7 — Provedores externos e roteamento [MVP-7]
**Entregas:** OpenAI/Gemini, credenciais protegidas, seleção automática/manual, política local-first, estimativa de custo e fallback autorizado.  
**Aceite:** trocar modelo sem perder tema; chaves não aparecem no browser/log; falha de provedor não envia conteúdo a outro sem permissão.

### Fase 8 — Polimento, acessibilidade e preparação comercial
**Entregas:** modo foco, metas, conquistas, preferências, backup/restauração, exportações, auditoria de licenças, testes E2E, documentação de instalação e empacotamento.  
**Aceite:** instalação limpa reproduzível; backup restaura notas/desenhos/trilhas; auditoria de segurança e licença documentada.

**Marco recomendado para primeiro uso real:** fases 0–3 (estudo funcional com trilhas); **MVP completo da visão inicial:** fases 0–5; materiais e multi-IA entram antes de uma versão pública ampla. Todas as funcionalidades essenciais e importantes permanecem no roadmap, mas não precisam ser entregues no primeiro marco.

## 10. Backlog prioritário (ordem por dependências)

- [x] B001 Configurar repositórios independentes, lint, format, typecheck e CI.
- [x] B002 Definir ADRs de stack, armazenamento, contratos e streaming.
- [x] B003 Implementar SQLite, migrations e repositórios de temas/conversas.
- [x] B004 Criar shell React, navegação, tema visual e estados de UI.
- [x] B005 Integrar Ollama com descoberta de modelos, healthcheck e streaming.
- [x] B006 Persistir mensagens e tratar interrupções de geração.
- [ ] B007 Definir schema versionado de blocos e renderer seguro.
- [ ] B008 Implementar quatro modos e prompts testáveis.
- [ ] B009 Criar banco de exercícios e correção com evidências.
- [ ] B010 Implementar planejamento editável de trilhas.
- [ ] B011 Implementar jobs e geração incremental de módulos.
- [ ] B012 Implementar resumos estruturados e controle de contexto.
- [ ] B013 Criar cadernos, pastas e páginas de rich text.
- [ ] B014 Implementar seleção de resposta → recorte com proveniência.
- [ ] B015 Integrar canvas de desenho editável e autosave.
- [ ] B016 Implementar flashcards, FSRS e agenda de revisões.
- [ ] B017 Implementar métricas de progresso, domínio e retenção.
- [ ] B018 Implementar XP, níveis e conquistas leves.
- [ ] B019 Implementar importação de materiais e pesquisa local.
- [ ] B020 Implementar autorização explícita de pesquisa web.
- [ ] B021 Implementar adaptadores OpenAI/Gemini e cofre de credenciais.
- [ ] B022 Implementar roteador automático com override manual.
- [ ] B023 Implementar modo foco, acessibilidade e configurações.
- [ ] B024 Implementar backup, restauração, exportação e instalação.
- [ ] B025 Executar testes de compatibilidade em GPU 6 GB e auditoria comercial.

## 11. Estratégia de testes e indicadores

**Automatizados:** unitários para domínio/FSRS/XP, integração SQLite/API, contratos JSON, falhas simuladas de provedores, E2E de fluxos críticos, segurança de uploads e consentimento.  
**Manuais com LLM:** bateria de assuntos variados (programação, idiomas, história, matemática), modelos pequenos quantizados, respostas longas, prompts adversariais e recuperação após interrupção.  
**Métricas internas opcionais:** tempo até primeira resposta, taxa de JSON válido, taxa de retry, sucesso de geração de módulo, erros de persistência, tempo de carregamento, taxa de revisão concluída. Não medir/registrar dados pessoais sem necessidade e consentimento apropriado.

## 12. Riscos e mitigação

| Risco | Mitigação |
|---|---|
| Modelo pequeno alucina ou gera JSON inválido | RAG, schemas, retry limitado, fallback, sinalização de incerteza |
| Contexto cresce indefinidamente | Resumos estruturados, seleção de trechos, budgets por tarefa |
| GPU 6 GB não comporta modelo escolhido | Perfis, quantização, contexto ajustável, CPU e avisos |
| Conteúdo de curso gerado cedo demais | Planejamento leve e geração lazy com cache/versionamento |
| Caderno perde desenhos ou texto | Autosave, controle de versão, backups e testes de recuperação |
| Licença de canvas/modelo incompatível com venda | Auditoria de licenças antes de adotar e antes do lançamento |
| Custos inesperados de APIs | Mostrar modelo efetivo, estimar custo, limites e confirmação |
| Pesquisa externa sem permissão | Gate de consentimento no backend, não apenas no frontend |
| Métricas de aprendizagem enganosas | Separar conclusão, domínio e retenção; mostrar incerteza |
| Execução insegura de código em exercícios | Sandbox isolada ou correção sem execução no MVP |

## 13. Decisões pendentes (não presumir)

1. **Nome e identidade visual** do produto.
2. **Sistema operacional-alvo inicial** (Windows prioritário? macOS/Linux?).
3. **Política de licenças**: código proprietário, open-core ou outra estratégia comercial.
4. **Licença e escolha final do canvas** (tldraw vs Excalidraw vs alternativa compatível).
5. **Mecanismo de pesquisa web** e custos/termos do provedor; manter interface abstrata até escolher.
6. **Lista de modelos Ollama recomendados** após benchmark real no hardware de 6 GB.
7. **Formato de exportação/importação** de caderno e desenhos; preservar formato editável.
8. **Autenticação/sincronização futura**: apenas preparar fronteiras, não implementar sem decisão.
9. **Escopo de execução de exercícios de código**: não executar código arbitrário antes de projetar sandbox.
10. **Padrão de segurança para chaves** conforme SO e forma de distribuição.

Quando uma decisão pendente bloquear uma implementação, o agente deve apresentar alternativas, trade-offs e pedir confirmação, em vez de inventar uma escolha silenciosa.

## 14. Definition of Done global

Uma funcionalidade está concluída somente se:

- [ ] Implementação real e integrada (sem mocks disfarçados).
- [ ] Tipos, schemas e validações definidos.
- [ ] Persistência e migrações corretas, se aplicáveis.
- [ ] Estados de carregamento, vazio, erro e cancelamento tratados.
- [ ] Segurança, privacidade e consentimento verificados.
- [ ] Testes relevantes executados e resultados registrados.
- [ ] Interface consistente e acessível.
- [ ] Comentários/docstrings necessários em pt-BR.
- [ ] Documentação e exemplos atualizados.
- [ ] Pendências, limitações e decisões não verificadas declaradas.

## 15. Instrução operacional para o agente implementador

> Leia este planejamento integralmente antes de implementar. Comece pela Fase 0 e proponha as decisões arquiteturais necessárias. Não implemente tudo de uma vez. Em cada incremento, apresente plano, arquivos a modificar e critérios de aceite; escreva código testável e execute verificações. Nunca invente resultados de testes, documentação, APIs ou funcionalidades. Se não souber ou não puder verificar algo crítico, pergunte ou interrompa a parte bloqueada. Comentários e docstrings em português brasileiro. Não avance para fases seguintes sem alinhar escopo e dependências.
