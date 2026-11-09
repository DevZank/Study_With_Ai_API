# Contrato HTTP — Marcos 1–3

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
