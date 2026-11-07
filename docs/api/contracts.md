# Contrato HTTP — Marco 1

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
