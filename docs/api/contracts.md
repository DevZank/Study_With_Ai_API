# Contrato HTTP — Marcos 1–5

A API publica sua descrição em `/openapi.json`. Base: `/api/v1`. O frontend acessa a mesma base pelo proxy Vite. Nenhum arquivo de código é importado entre repositórios.

| Método e rota | Entrada / resultado |
| --- | --- |
| GET /health | `{"status":"ok"}`; apenas disponibilidade HTTP |
| GET /topics | Filtros `status=active\|archived\|deleted`, `q`, `limit`, `cursor` |
| POST /topics | `{"title":"Tema"}`; HTTP 201 |
| GET /topics/{id} | Tema, inclusive na lixeira |
| PATCH /topics/{id} | `title` e/ou `status` não nulos |
| DELETE /topics/{id} | Lixeira reversível, sem remoção física |
| GET /topics/{id}/conversations | Conversas paginadas |
| POST /topics/{id}/conversations | `{"title":"Conversa"}`; HTTP 201 |
| GET /conversations/{id}/messages | Histórico paginado em ordem cronológica |
| GET /conversations/{id}/jobs | Até 20 jobs recentes, para recuperar o estado |
| POST /conversations/{id}/messages | `{"content":"Pergunta","model_id":"modelo:tag","request_id":"UUID"}`; HTTP 202 com job |
| GET /ai/models | `{"models":["modelo:tag"],"provider":"ollama","local_only":true}` |
| GET /jobs/{id} | Estado, modelo, mensagem associada e eventual erro seguro |
| GET /jobs/{id}/events | `text/event-stream` |
| POST /jobs/{id}/cancel | Cancelamento idempotente; preserva conteúdo parcial |

Listagens paginadas retornam `{"items":[],"next_cursor":null}`. Uma chave `request_id` deve ser reutilizada ao repetir o mesmo envio após uma falha de rede. Não usar a chave com outro conteúdo.

Jobs e mensagens usam os estados `running`, `completed`, `failed`, `cancelled` ou `interrupted`. Apenas mensagens completas entram no contexto do modelo. Não há novos envios em temas arquivados ou na lixeira.

Erros seguem `{"error":{"code":"CODIGO","message":"Mensagem segura.","details":{},"request_id":"UUID"}}`. Entre os códigos: `MODEL_TIMEOUT`, `OLLAMA_UNAVAILABLE`, `STREAM_INTERRUPTED`, `CONTEXT_LIMIT`, `GENERATION_ACTIVE` e `IDEMPOTENCY_CONFLICT`.

Cada evento SSE contém `event_id`, `job_id`, `job` e `message`. O payload é um snapshot completo: substituir a mensagem pelo ID, sem concatenar snapshots. Estados parciais ficam visíveis como provisórios. Reconectar reenvia o estado atual do banco, sem depender do processo anterior. O cancelamento é feito pela rota própria, não pelo fechamento do EventSource.

## Extensões do Marco 2

- GET /conversations/{id}: consulta a conversa e active_mode.
- PATCH /conversations/{id}: recebe active_mode = study, memorize, learn ou practice.
- POST /conversations/{id}/messages aceita mode opcional e response_format=text ou blocks. O formato padrão text preserva clientes antigos; practice exige blocks.
- Mensagens acrescentam mode, response_format, notice e document. O documento público segue [content-v1.schema.json](content-v1.schema.json). document_json interno e gabaritos não são serializados.
- GET /exercises/{id}: enunciado, alternativas, dicas já reveladas e hints_remaining. solution e explanation são nulos antes da primeira tentativa.
- POST /exercises/{id}/hints: revela a próxima dica; não revela a solução.
- POST /exercises/{id}/attempts: recebe response (string) e request_id (UUID). Retorna tentativa persistida com score 0/1 em questões objetivas ou null em questões abertas.
- GET /exercises/{id}/attempts: lista as tentativas do perfil local.

No fluxo blocks, os eventos SSE não contêm JSON bruto ou rascunhos de gabaritos: o documento aparece somente depois da validação e do commit. Em caso de JSON inválido após uma repetição, o job retorna INVALID_CONTENT, sem exercício parcial. No fluxo text legado, mantém-se o streaming textual.

## Extensões do Marco 3

| Método e rota | Entrada / resultado |
| --- | --- |
| POST /trails/plan | topic_id, objective, prior_knowledge e preferences opcionais, module_count (1–8, padrão 5), model_id, request_id; 202 TrailJob |
| GET /topics/{id}/trails | Paginação limit/cursor; items de Trail |
| GET /trails/{id} | trail, modules com units/versions/summaries, completed_units, total_units |
| PATCH /trails/{id} | expected_version e title; plano atualizado |
| POST /trails/{id}/modules | expected_version e plan; 201 plano atualizado |
| PATCH /modules/{id} | expected_version, plan e/ou archived; plano atualizado |
| PATCH /trails/{id}/modules/order | expected_version e module_ids com todos os módulos ativos |
| GET /modules/{id}/lessons | Metadados das unidades; não gera conteúdo |
| POST /modules/{id}/generate | model_id, request_id, unit_id opcional (primeira por padrão), granularity=auto, force_regenerate=false; 202 TrailJob |
| GET /units/{id}/versions/{version_id} | version, message pública, summaries e stale |
| POST /units/{id}/complete | version_id, difficulties opcional, model_id, request_id; 202 TrailJob |
| GET /topics/{id}/trail-jobs | Até 30 jobs, incluindo planejamento antes da criação da trilha |
| GET /trails/{id}/jobs | Até 30 jobs da trilha |
| GET /trail-jobs/{id} | Snapshot TrailJob |
| POST /trail-jobs/{id}/cancel | Cancela operação e eventual job interno |
| GET /trail-jobs/{id}/events | SSE com event job.started/completed/failed/cancelled/interrupted e payload {job}; sem conteúdo bruto |

ModulePlan contém title, objectives (1–6), criteria (1–4), estimated_minutes (5–180) e lesson_titles (1–6); textos curtos têm até 160 caracteres. O plano não contém aulas geradas. TrailJob contém kind=plan/unit/summary, status, target_id, trail_id, result_id, cached e erro seguro. result_id identifica respectivamente trilha, versão ou resumo. O fingerprint e child_job_id são metadados de coordenação, sem prompts ou gabaritos.

Repetições da mesma operação devem manter request_id. Nova geração ou nova tentativa após job falho usa novo UUID. A revisão esperada evita sobrescrever edição concorrente; STALE_PLAN exige recarregar. O cache não atualiza versões antigas quando o plano muda: o cliente deve pedir force_regenerate explicitamente. Versões e resumos têm IDs próprios e são preservados. O campo context é um snapshot JSON de resumos limitados, sem histórico bruto. Veja a [ADR 0004](../architecture/0004-incremental-trails.md) para orçamento, contagem de progresso e recuperação de interrupções.

## Extensões do Marco 4

| Método e rota | Entrada / resultado |
| --- | --- |
| GET /notebooks | Array de cadernos locais globais/por tema; temas na lixeira ficam ocultos |
| POST /notebooks | title, topic_id opcional, trail_id opcional; 201 Notebook |
| GET /notebooks/{id}/folders | Array de pastas |
| POST /notebooks/{id}/folders | title, parent_id opcional; 201 Folder |
| PATCH /folders/{id} | title, parent_id opcional, expected_version; Folder atualizado |
| GET /notebooks/{id}/pages | Array de páginas; q pesquisa título/texto/tags, até 120 caracteres |
| POST /notebooks/{id}/pages | title, folder_id opcional; 201 NotePage com quadro vazio |
| GET /pages/{id} | NotePage com document JSON, tags, topic_ids e linked_page_ids |
| PATCH /pages/{id} | title, notebook_id, folder_id, document, tags, topic_ids, linked_page_ids, expected_version e operation_id; NotePage atualizado |
| GET /pages/{id}/revisions | Até 30 revisões recentes com snapshot completo |
| GET /pages/{id}/clippings | Recortes imutáveis com origem e intervalo |
| POST /pages/{id}/clippings | message_id, start, end, selected_text, expected_version, operation_id; 201 NotePage com cópia acrescentada |
| GET /messages/{id}/clipping-source | text canônico e source construídos pelo backend, somente resposta concluída de IA |
| GET /pages/{id}/drawing | Drawing com version e scene |
| PUT /pages/{id}/drawing | scene, expected_version e operation_id; Drawing atualizado |

As listagens de caderno usam arrays nesta versão; não utilizam o envelope paginado de temas/conversas. Não importar contratos Python no frontend: a descrição completa está no OpenAPI do backend em execução, e o consumidor valida os resultados com Zod.

Todos os IDs de entrada são UUID. A hierarquia de pastas é limitada a oito níveis e não admite ciclos; não se pode mover uma página para uma pasta de outro caderno. NotePage tem version para concorrência; o desenho tem version independente. NOTE_CONFLICT (409) exige conciliar o rascunho com a versão atual. operation_id deve ser reutilizado somente na repetição do mesmo envio. Atualizações de página, revisão e recorte são transacionais.

Documentos TipTap são JSON com nós/marcas permitidos: parágrafos, títulos, listas, citações, código, tabelas, fórmulas e formatação básica. Não são aceitos HTML arbitrário, imagens remotas ou links javascript. Limites: 250.000 caracteres de JSON, 3.000 nós, profundidade 16, 20 tags/temas/vínculos. Desenhos usam type=excalidraw, version=2, source=study-local, elements, appState e files; apenas imagens locais PNG/JPEG/WebP, até 500 KB cada, dez arquivos e 2,5 MB por cena. O limite HTTP de 3 MB é exclusivo de /pages e /notebooks; demais rotas mantêm 32 KB.

O intervalo do recorte é [start,end), em pontos de código Unicode no text da origem canônica, e deve corresponder exatamente a selected_text. source registra tema/conversa/mensagem/data/modelo e os IDs de trilha/módulo/unidade/versão quando existentes. É preenchido pelo servidor, nunca aceito do cliente. Soluções privadas de exercícios não fazem parte dessa representação. O documento recebe uma cópia editável; modificar a cópia preserva recorte e resposta original. Veja a [ADR 0005](../architecture/0005-local-notebooks.md).

## Extensões do Marco 5

| Método e rota | Entrada / resultado |
| --- | --- |
| GET /topics/{topic_id}/flashcards | Filtros `include_archived=true\|false`, `at` (timestamp ISO-8601 UTC opcional); array de `FlashcardView` (`{card, review_state, estimated_retention, due}`) |
| POST /topics/{topic_id}/flashcards | `front`, `back`, `concept_name` opcional, `operation_id` (UUID), `created_at` opcional; 201 `FlashcardView` com estado inicial FSRS (`new`) |
| POST /messages/{message_id}/flashcards | `block_id`, `concept_name` opcional, `operation_id` (UUID); 201 `FlashcardView` importado de bloco validado concluído de IA |
| PATCH /flashcards/{flashcard_id} | `front`, `back`, `concept_name`, `archived`, `expected_version` e `operation_id`; `FlashcardView` atualizado |
| GET /flashcards/{flashcard_id}/history | Histórico cronológico de eventos FSRS (`ReviewEvent[]`) |
| GET /reviews/due | Filtros `topic_id` opcional, `at` (timestamp ISO-8601 UTC opcional), `limit` (1–100); array de `FlashcardView` vencidos |
| POST /reviews/{flashcard_id}/grade | `rating` (`1..4`), `request_id` (UUID), `reviewed_at` (ISO-8601 UTC opcional); `ReviewGradeView` (`{card, review_state, event}`) |
| GET /progress/topics/{topic_id} | Indicadores separados (`completion`, `mastery`, `retention`), `explanations`, `recommendations` e `gamification` |
| GET /progress/overview | Visão agregada com `calculated_at`, `due_count`, `active_topics_count` e `gamification` |
| PATCH /progress/preferences | `{"hide_gamification":true\|false}`; atualiza a preferência de ocultar/exibir gamificação (`ProgressPreference`) |

O agendador FSRS é determinístico: informar o mesmo `reviewed_at` em UTC com a mesma sequência de avaliações `rating` (`1` = Errei/Novamente, `2` = Difícil, `3` = Bom, `4` = Fácil) produz exatamente a mesma estabilidade, dificuldade, recuperabilidade e `due_at`. A avaliação é idempotente por `request_id`.

Os três indicadores (`completion`, `mastery` e `retention`) nunca são combinados em nota única. Quando não há evidências suficientes (`evidence_count = 0` para conceitos ou `reviewed_cards = 0` para retenção), `estimated_score` / `estimated_retention` retornam `null`. O razão `xp_events` impede ganhos duplicados na repetição do mesmo exercício, na repetição de conclusão da mesma unidade ou na revisão de cartões não vencidos. Veja a [ADR 0006](../architecture/0006-memorization-and-progress.md).
