# ADR 0002 — Temas e conversas locais (Marco 1)

Aceito para B003–B006, em 07/11/2026.

## Persistência e recuperação

SQLAlchemy 2.1 e Alembic gerenciam SQLite com WAL, chaves estrangeiras e timeout de escrita. A migração inicial cria perfil local com UUID fixo, temas, conversas, mensagens e jobs. Cada registro de conteúdo tem proprietário e datas UTC. O caminho padrão é `data/study.sqlite3`, relativo ao repositório backend; `STUDY_DB_PATH` permite selecionar outro arquivo na configuração do processo.

Aplicar migrações é uma operação explícita antes de iniciar o servidor. A migração inicial não possui downgrade destrutivo: para reverter uma instalação com dados, parar a API e restaurar um backup confirmado e validado. Novas migrações exigem plano próprio. Os testes usam arquivos temporários e conferem que o esquema migrado corresponde aos modelos.

A gravação de uma pergunta, da resposta inicialmente vazia e do job ocorre em uma transação. O banco impede dois jobs ativos na mesma conversa e repetições do identificador da requisição. A mesma chave com payload diferente retorna conflito. O serviço limita o contexto sem cortar silenciosamente o histórico.

Executar uma única instância da API e um único worker por banco. Na inicialização, jobs ainda ativos são marcados como interrompidos; o texto parcial é preservado. A coordenação entre múltiplos processos não está implementada. No encerramento normal, as gerações são canceladas.

## Exclusão reversível

Arquivar mantém leitura do histórico, mas bloqueia novos envios. Excluir move o tema para a lixeira, sem apagar conversas ou mensagens. Restaurar retorna o tema ao estado ativo. Não há expiração ou exclusão física automática neste marco. Durante geração ativa, alterações no tema retornam conflito.

## Ollama, privacidade e limites

O adaptador HTTP usa somente `127.0.0.1:11434`, sem proxies de ambiente ou redirecionamentos. A interface exige seleção manual de modelo instalado. Entradas identificadas como cloud são removidas da lista e a metadata do modelo é conferida antes do envio. Modelos remotos e sem capacidade de conversação são recusados, sem fallback.

Timeout de conexão: 5 segundos; leitura de geração: 90 segundos; duração total: 180 segundos. O contexto solicitado é 4096 tokens e a geração é limitada a 1024 tokens. A aplicação aceita até 4000 caracteres por pergunta, 30 mensagens completas e 12 mil caracteres de histórico por conversa. Ao atingir o limite, orienta criar outra conversa; resumos e roteamento pertencem a marcos posteriores. Respostas têm limite adicional de 50 mil caracteres.

A leitura NDJSON exige sinal final de conclusão e valida cada bloco. Falhas, timeout e cancelamento mantêm o texto parcial com estado explícito. Cancelar fecha o stream HTTP desta geração; não encerra o serviço Ollama nem outros modelos.

A primeira tentativa real com qwen3.5:4b falhou por timeout de leitura. A repetição com o modelo carregado passou. Isso não é benchmark nem recomendação de modelo para 6 GB.

## REST, SSE e interface

Contratos em `/api/v1`, schemas Pydantic e validação Zod no frontend. O frontend usa TanStack Query para dados de servidor e Tailwind para a base de estilos; o visual é provisório e não define a identidade do produto.

O stream SSE contém snapshots completos e idempotentes da mensagem, inclusive nos eventos chamados `generation.delta`. Isso permite reconectar sem duplicar texto. Há eventos `job.started`, `job.completed`, `job.failed`, `job.cancelled` e `job.interrupted`. O fechamento da aba não cancela o job; é possível retomar a observação. Eventos repetidos substituem a mensagem pelo ID.

Mensagens são apresentadas como texto, sem HTML ou código executável. Blocos estruturados e modos pedagógicos entram no Marco 2. Paginação usa cursor opaco baseado no ID do item e limite de até 100 por página. As consultas de histórico ficam restritas à conversa; listagens iniciais ainda são paginadas em memória, adequadas ao início local, sem promessa de escala.

Bind e proxy em loopback, verificação de Host e Origin para escritas e limite de corpo de 32 KiB protegem a API local. Não há autenticação nem suporte a exposição em rede. Logs de acesso devem ficar desabilitados para evitar registrar consultas de pesquisa; os logs da aplicação registram códigos e IDs, sem prompts.

## Dependências e fontes consultadas

Versões resolvidas e testadas: SQLAlchemy 2.1.8, Alembic 1.20.1, TanStack Query 5.107.1, Tailwind 4.3.5, Zod 4.6.7 e Playwright 1.65.0. As duas primeiras bibliotecas, Query, Tailwind e Zod declaram MIT; Playwright declara Apache-2.0. Mako declara MIT e MarkupSafe BSD-3-Clause. Os metadados de licença do lockfile npm não ficaram sem identificação; aparecem MIT, Apache-2.0, 0BSD, ISC, MPL-2.0 e BSD-3-Clause. Mantêm-se as obrigações de avisos e a auditoria dos artefatos distribuídos prevista em B025.

Documentação consultada via Context7: [ORM SQLAlchemy](https://docs.sqlalchemy.org/en/20/orm/declarative_tables.html), [migrações Alembic](https://alembic.sqlalchemy.org/en/latest/cookbook.html) e [API Ollama](https://github.com/ollama/ollama/blob/main/docs/api.md). O suporte das versões efetivamente instaladas foi confirmado pelos testes locais; não se presume compatibilidade futura só pela documentação.

