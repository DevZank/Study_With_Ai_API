# TASKS.md — Plano de execução e acompanhamento

> **Fonte de requisitos:** `PLANEJAMENTO_PLATAFORMA_ESTUDOS_IA.md`  
> **Regras para agentes:** `AGENTS.md`  
> **Estado atual:** Marcos 0–4 verificados localmente no Windows; Marco 5 não iniciado.
> **Estratégia:** concluir uma fase por vez, sem antecipar funcionalidades não aprovadas.

> Referência principal do progresso integrado: TASKS.md do repositório backend. A cópia do frontend é um retrato que deve ser conciliado explicitamente ao atualizar tarefas compartilhadas.

## Legenda e uso

- `[ ]` Pendente; `[x]` Concluído **com evidência**. Para tarefas em andamento, manter `[ ]` e anotar `EM ANDAMENTO`.
- `BLOQUEADO`: requer decisão, dependência ou recurso não disponível.
- Cada tarefa tem um ID estável `B001`–`B025`, correspondente ao backlog da especificação.
- **Não marcar tarefas como concluídas por geração de código apenas**. Conferir os critérios de aceite e registrar comando, resultado e data.
- Registrar mudanças de escopo e decisões arquiteturais em `docs/architecture/` (ADR) quando o repositório existir.

## Marco 0 — Fundação [BLOQUEANTE]

- [x] **B001 — Configurar repositórios independentes, qualidade e CI.** Manter código, documentação, contratos, scripts pertinentes e CI dentro de cada repositório; configurar ambiente Node/Python, lint, format, typecheck, testes básicos, lockfiles e CI. **Aceite:** frontend/backend iniciam localmente; healthcheck responde; checks básicos passam. **Dep.:** nenhuma.
- [x] **B002 — Documentar decisões estruturais.** Criar ADRs de stack, contratos, SQLite, SSE, execução local, segurança e política de dependências comerciais. **Aceite:** decisões justificadas, riscos registrados e nenhuma escolha bloqueante assumida. **Dep.:** nenhuma; coordena B001.

**Gate do marco 0:** ambiente reproduzível, sem segredos no repositório, documentação de setup funcional e decisões bloqueantes tratadas.

## Marco 1 — Temas, conversas e Ollama [MVP-1]

- [x] **B003 — Banco e repositórios.** SQLite, Alembic, entidades iniciais de tema/sessão/mensagem, CRUD e testes de migração. **Aceite:** criar/editar/arquivar tema e persistir conversas após reinício. **Dep.:** B001, B002.
- [x] **B004 — Shell React e navegação.** Sidebar de temas, dashboard, rotas, estados vazios/erro/carregamento, layout responsivo. **Aceite:** navegar entre temas e criar novo tema por API real. **Dep.:** B001, B003.
- [x] **B005 — Integração Ollama.** Diagnóstico, listagem de modelos, envio de prompts, streaming SSE, timeouts e erros. **Aceite:** resposta real de modelo instalado; ausência do Ollama tratada. **Dep.:** B001, B002.
- [x] **B006 — Persistência de mensagens e cancelamento.** Salvar turnos, estado de geração e recuperação após falha. **Aceite:** recarregar preserva histórico; cancelar interrompe a operação sem corromper a sessão. **Dep.:** B003, B004, B005.

**Gate do marco 1:** VERIFICADO em 07/11/2026 com bancos temporários: criar tema, conversar com Ollama, cancelar, recarregar e recuperar histórico após reiniciar a aplicação. A primeira geração real teve timeout; a repetição com modelo carregado passou.

## Marco 2 — Quatro modos e respostas estruturadas [MVP-2]

- [x] **B007 — Schemas e renderer de blocos.** Tipos versionados para explicação, código, fórmulas, perguntas, tabelas etc.; validação e fallback seguro. **Aceite:** JSON inválido não quebra UI nem executa conteúdo arbitrário. **Dep.:** B005, B006.
- [x] **B008 — Estudar, Memorizar, Aprender, Praticar.** Estratégias/prompt templates separados, troca de modo mantendo tema e contexto. **Aceite:** comportamentos distintos e verificáveis; histórico preservado. **Dep.:** B007.
- [x] **B009 — Exercícios e correção.** Tentativas persistidas, dicas progressivas, feedback, gabarito protegido e avaliação determinística quando possível. **Aceite:** responder questão registra tentativa e feedback; gabarito não vaza antes. **Dep.:** B003, B007, B008.

**Gate do marco 2:** VERIFICADO em 07/11/2026: quatro modos na mesma conversa com histórico preservado, blocos validados, exercício real e tentativa persistida. Banco de uso real não foi alterado; revisão 0002 validada em bancos temporários e atualização de histórico legado.

## Marco 3 — Trilhas e geração incremental [MVP-3]

- [x] **B010 — Planejamento editável de trilhas.** Formulário de objetivo, plano inicial somente com metadados, editar/reordenar módulos. **Aceite:** gerar trilha sem gerar aulas futuras; edição persiste. **Dep.:** B003, B007, B008.
- [x] **B011 — Geração sob demanda.** Jobs canceláveis, granularidade automática módulo/aula, cache e versionamento. **Aceite:** abrir módulo 1 gera apenas a unidade necessária; módulos seguintes continuam não gerados. **Dep.:** B010.
- [x] **B012 — Resumo estruturado e controle de contexto.** Resumir conclusões, dificuldades e conceitos; limitar contexto enviado ao modelo. **Aceite:** próximo módulo usa resumo persistido, não todo histórico bruto. **Dep.:** B011, B009.

**Gate do marco 3:** VERIFICADO em 08/11/2026 com bancos temporários: plano de cinco módulos sem aulas futuras, edição persistida, geração incremental, versões/cache, cancelamento, resumo persistido e continuidade limitada. Ollama real qwen3.5:4b validado por API; navegador validado com provedor determinístico exclusivo de teste. Migração 0002→0003 preserva histórico sintético. Banco pessoal não foi migrado.

## Marco 4 — Caderno livre [MVP-4]

- [x] **B013 — Caderno global e por tema.** Pastas, páginas, editor rico, vínculos, pesquisa e persistência. **Aceite:** criar/editar/mover notas e recuperar após reiniciar. **Dep.:** B003, B004.
- [x] **B014 — Seleção de resposta → caderno.** Selecionar trecho, salvar com fonte, tema e módulo, editar cópia sem alterar original. **Aceite:** recorte mantém proveniência e funciona nos dois tipos de caderno. **Dep.:** B007, B013.
- [x] **B015 — Desenho livre editável.** Canvas com traços, formas, setas, texto, zoom/pan, desfazer/refazer, autosave e exportação; verificar licença comercial da biblioteca antes de escolher. **Aceite:** desenhar, recarregar e continuar editando sem perda. **Dep.:** B013, decisão de biblioteca/licença.

**Gate do marco 4:** VERIFICADO em 08/11/2026, com bancos temporários: cadernos globais/por tema/trilha, texto rico, pastas, vínculos, busca, movimentação, recortes com origem e desenho recuperado após recarga. Usuário aprovou Excalidraw e .excalidraw/PNG. Bibliotecas principais MIT e avisos de fontes conferidos/preservados. API com conflitos e histórico; rascunho recuperado após falha de rede. Banco pessoal não migrado.

## Marco 5 — Memorização e progresso [MVP-5]

- [ ] **B016 — Flashcards e revisão espaçada.** Gerar/editar cartões, FSRS, fila de revisão, agendamento determinístico e testes. **Aceite:** revisões sobrevivem a reinício; vencimentos são reproduzíveis. **Dep.:** B008, B003.
- [ ] **B017 — Métricas pedagógicas.** Progresso por trilha, domínio por conceito e retenção estimada, com explicação das métricas. **Aceite:** indicadores separados e calculados a partir de eventos reais. **Dep.:** B009, B010, B016.
- [ ] **B018 — Gamificação leve.** XP, níveis, conquistas simples, proteção contra ganho repetitivo artificial. **Aceite:** recompensas registradas por ações válidas; não premiar spam. **Dep.:** B017.

**Gate do marco 5:** ciclo de aprender, praticar, memorizar e acompanhar progresso funcional.

## Marco 6 — Materiais e fontes [MVP-6]

- [ ] **B019 — Importação, busca local e RAG.** Upload seguro, PDF/texto, extração, FTS5, recuperação de trechos e fontes verificáveis; embeddings opcionais. **Aceite:** resposta pode apontar trecho real de material enviado. **Dep.:** B003, B007.
- [ ] **B020 — Pesquisa web com autorização.** Solicitar consentimento por operação, permitir negar/cancelar, registrar decisão e separar pesquisa de uso de API externa. **Aceite:** nenhuma consulta web é iniciada sem autorização específica. **Dep.:** B019, decisão de provedor de pesquisa.

**Gate do marco 6:** materiais locais consultáveis; pesquisa externa apenas após permissão.

## Marco 7 — Multi-IA e roteamento [MVP-7]

- [ ] **B021 — Adaptadores externos e credenciais.** OpenAI/Gemini, testes de conexão, armazenamento seguro de chaves, políticas de privacidade e custos estimados. **Aceite:** chave não aparece em logs/respostas; uso externo informado. **Dep.:** B005, decisão de proteção de chaves.
- [ ] **B022 — Seleção automática com override.** Roteamento por tarefa, custo, recursos e capacidade; escolha manual; fallback sem envio externo silencioso. **Aceite:** troca de modelo preserva sessão; fallback exige autorização quando altera destino dos dados. **Dep.:** B021, B012.

**Gate do marco 7:** provedores intercambiáveis com privacidade, escolha e falhas tratadas.

## Marco 8 — Qualidade, distribuição e preparação comercial

- [ ] **B023 — Modo foco, acessibilidade e preferências.** Controle de ritmo, animações reduzidas, atalhos, contraste, configurações. **Aceite:** fluxos principais acessíveis por teclado e testados. **Dep.:** B004, B017.
- [ ] **B024 — Backup, restauração, exportação e instalação.** Preservar banco, anexos e desenhos editáveis; instalação reproduzível. **Aceite:** backup restaurado em instalação limpa mantém conteúdo e vínculos. **Dep.:** B013, B015, B019.
- [ ] **B025 — Compatibilidade e auditoria comercial.** Benchmark real com GPU de 6 GB, análise de dependências/licenças, privacidade, segurança e documentação de distribuição. **Aceite:** relatório com hardware/modelos medidos, resultados reproduzíveis e bloqueios de licença resolvidos. **Dep.:** B022, B024.

**Gate do marco 8:** release candidate testado e documentado; não declarar pronto para venda sem validação jurídica e operacional aplicável.

## Decisões em aberto (registrar antes de implementar o item afetado)

- [ ] **D001** Nome e identidade visual do produto.
- [x] **D002** Windows confirmado como sistema operacional prioritário na primeira distribuição.
- [ ] **D003** Política inicial confirmada: adotar dependências compatíveis com uso comercial; escolher a licença do produto antes da distribuição.
- [ ] **D004** Biblioteca de desenho e política de exportação em formato editável.
- [ ] **D005** Serviço de pesquisa web, limites e custos.
- [ ] **D006** Modelos Ollama recomendados após benchmark de 6 GB.
- [ ] **D007** Formatos de importação/exportação de cadernos e desenhos.
- [ ] **D008** Autenticação e sincronização futura (não implementar sem decisão).
- [ ] **D009** Necessidade e isolamento de execução de exercícios de programação.
- [ ] **D010** Proteção de chaves conforme sistema operacional e empacotamento.

## Registro de execução

> Atualizar ao final de cada incremento. **Não preencher evidências fictícias.**

| Data | Tarefa | Estado | Evidência (comando/resultado) | Bloqueios / observações |
|---|---|---|---|---|
| 06/11/2026 | B001 | CONCLUÍDO | `npm ci` e instalação de `requirements.lock` em ambiente limpo passaram; `pip check`, lint, formato e tipagem passaram nos dois ambientes; Vitest: 2 testes; pytest: 1 teste; build Vite concluído. HTTP 200 na página inicial, no healthcheck direto e pelo proxy, com `status=ok` nos dois healthchecks. | CI remoto NÃO EXECUTADO (workflow criado localmente); teste visual em navegador NÃO EXECUTADO. Diagnóstico: Ollama instalado, serviço indisponível; GPU de 6 GB não testada. |
| 06/11/2026 | B002 | CONCLUÍDO | ADR 0001 registra stack, contratos, SQLite, SSE, loopback, segurança e triagem de licenças via lockfile npm e metadados Python. D002 e política inicial de D003 aprovadas. | Escolha da licença do produto e auditoria de redistribuição seguem pendentes. |
| 06/11/2026 | B001 | REORGANIZAÇÃO VERIFICADA | Aplicações movidas para `Frontend/` e `Backend/`. `npm ci`, formatação, lint, tipagem, Vitest (2 testes) e build passaram. Ruff, mypy e pytest (1 teste) passaram no backend. | CI remoto e teste HTTP com os dois servidores após a mudança: NÃO EXECUTADOS. |
| 06/11/2026 | B001 | CONFIGURAÇÕES REORGANIZADAS | npm, lockfile e Prettier em `Frontend/`; ambiente Python recriado em `Backend/.venv/`; `.env.example` removido com aprovação. Instalações, checks, build e 3 testes passaram. HTTP 200 na página, na API e no proxy, com `status=ok` nos healthchecks. | CI remoto NÃO EXECUTADO. |
| 06/11/2026 | B001 | GIT SEPARADO | `git rev-parse` e `git status` confirmaram que o repositório existente agora está em `Backend/`, com o mesmo HEAD, branch e remoto. `Frontend/` segue sem Git e tem workflow próprio; verificação de formatação passou. | Commit, push, CI remoto e testes da aplicação NÃO EXECUTADOS neste ajuste. |

| 06/11/2026 | B001/B002 | REPOSITÓRIOS AUTOSSUFICIENTES | Regras, planejamento, tarefas, ADR, matriz e contrato HTTP presentes em ambos. Script de diagnóstico presente no backend. Links locais verificados. Frontend: formato, lint, tipagem, 2 testes e build passaram. Backend: pip check, Ruff, mypy e 1 teste passaram. Diagnóstico local: Ollama 0.40.15 respondeu. | Clone limpo, CI remoto, commit e push NÃO EXECUTADOS neste incremento. |

| 07/11/2026 | B003 | CONCLUÍDO | Migração Alembic 0001, comparação do esquema com metadata e persistência após reabrir SQLite verificadas. Perfil local, temas, conversas, mensagens e jobs com proprietário. Suíte final backend: python -m pytest -q, 12 passed e 1 skipped (teste real opcional). | Nenhum banco de uso real migrado; testes com arquivos temporários. Downgrade destrutivo bloqueado. |
| 07/11/2026 | B004 | CONCLUÍDO | npm run format:check, lint, typecheck, test (5 passed) e build passaram. npm run test:e2e: 2 passed, 1 skipped (real opcional). Navegação por teclado, responsividade 1280/390 px, criação por API real, arquivar/lixeira/restaurar e HTML exibido como texto verificados. Capturas inspecionadas. | Identidade visual permanece provisória. Build emite aviso sobre diretivas use client do TanStack Query; funcionamento validado em navegador. |
| 07/11/2026 | B005 | CONCLUÍDO | STUDY_TEST_OLLAMA_MODEL=qwen3.5:4b com pytest tests/test_real_ollama.py -q: 1 passed na repetição. E2E_REAL_MODEL=qwen3.5:4b com npm run test:e2e -- --grep "modelo local real": 1 passed. Listagem local, resposta real, SSE e falha do provedor verificados. | Primeira tentativa real falhou com MODEL_TIMEOUT; mantida como limitação documentada. GPU alvo de 6 GB NÃO TESTADA. Não há recomendação definitiva de modelo nem benchmark. |
| 07/11/2026 | B006 | CONCLUÍDO | Testes verificaram idempotência, impedimento de geração duplicada, cancelamento com fechamento do HTTP, preservação parcial após falha, recarga e recuperação de jobs após reiniciar a aplicação. API e navegador também cancelaram geração real do Ollama. | Somente uma instância/worker por banco. CI remoto, instalação limpa completa, commit e push NÃO EXECUTADOS neste incremento. |
| 07/11/2026 | B007 | CONCLUÍDO | Schema público 1.0 exportado, validação estrita, renderer permitido e gramática local por modo. pytest -q: 33 passed e 2 skipped (reais opcionais). npm test: 11 passed. Testados JSON inválido, blocos desconhecidos, fórmulas não confiáveis, ausência de gabaritos em mensagens/SSE, repetição limitada e falha de commit sem falso sucesso. | Rascunhos estruturados ficam ocultos e são descartados em falha/cancelamento. Nenhum banco de uso real migrado. |
| 07/11/2026 | B008 | CONCLUÍDO | Modos e mensagens persistidos; npm run test:e2e: 4 passed e 2 skipped (reais opcionais). Capturas desktop/celular inspecionadas. STUDY_TEST_OLLAMA_MODEL=qwen3.5:4b com pytest tests/test_real_content.py -q -s: 1 passed, com documentos reais nos quatro modos. | Primeira validação real rejeitou Memorizar; após restringir a gramática ao modo, a repetição passou. Sem benchmark de 6 GB. |
| 07/11/2026 | B009 | CONCLUÍDO | Migração aditiva 0002, gabaritos privados, dicas progressivas e tentativas idempotentes. Correção de múltipla escolha, verdadeiro/falso e lacunas testada; questão aberta com revisão sem nota. E2E_REAL_MODEL=qwen3.5:4b com npm run test:e2e -- --grep "exercício estruturado real": 1 passed; tentativa real recuperada após recarga. | Gabaritos gerados por IA podem conter erros. Não há avaliação semântica automática de questões abertas, execução de código ou métricas de domínio. |
| 07/11/2026 | B007–B009 | CHECKS | Backend: pip check, Ruff check/format e mypy passaram. Frontend: format:check, lint, typecheck, testes e build passaram. Contratos/ADRs atualizados e schema público conciliado entre repositórios. | CI remoto, instalação limpa completa e migração do banco pessoal NÃO EXECUTADOS. Build mantém avisos de diretivas use client de dependência. Commit e push NÃO EXECUTADOS. |
| 08/11/2026 | B010 | CONCLUÍDO | Plano de cinco módulos sem conteúdo futuro; edição/reordenação/adição/arquivamento e conflitos de revisão testados. Migração aditiva 0003 e atualização de histórico 0002 validadas em bancos temporários. | Divisão de unidades existentes é preservada ao editar metadados; outra divisão requer adicionar módulo. |
| 08/11/2026 | B011 | CONCLUÍDO | Testes cobrem geração de uma unidade, cache sem nova geração, duas versões preservadas, cancelamento e recuperação. E2E do Marco 3 passou no Edge com recarga e capturas desktop/celular. | Limite inicial de dez versões por unidade; uma instância da API por banco. |
| 08/11/2026 | B012 | CONCLUÍDO | Resumo persistido com dificuldades informadas e tentativas reais. Teste verifica máximo de três resumos e 4.500 caracteres. STUDY_TEST_OLLAMA_MODEL=qwen3.5:4b com pytest tests/test_real_trails.py: 1 passed em 137,90 s; segunda unidade real usa resumo da primeira. | Domínio/retenção não estimados; evidência do resumo é um snapshot de conclusão. |
| 08/11/2026 | B010–B012 | CHECKS | Backend: 37 passed, 3 skipped; Ruff, mypy e pip check aprovados. Frontend: 11 testes passaram; format/lint/typecheck/build aprovados; E2E 5 passed, 2 skipped. Contratos, ADR e TASKS conciliados entre repositórios. Ver docs/development/milestone3-validation.md. | CI remoto, banco pessoal, instalação limpa e benchmark de 6 GB NÃO EXECUTADOS. E2E real de trilha no navegador NÃO EXECUTADO; integração real validada por API. Commit/push NÃO EXECUTADOS. |

| 08/11/2026 | B013 | CONCLUÍDO | Migração 0004 aditiva; cadernos/pastas/páginas com proprietário, revisão e conflitos. Testes API de edição, movimentação, busca e reinício; E2E de texto rico, vínculo navegável e movimento entre cadernos. | Busca simples por caderno; FTS e anexos gerais são de B019. Rascunhos dependem do armazenamento do navegador. |
| 08/11/2026 | B014 | CONCLUÍDO | Recorte validado contra resposta persistida, intervalo Unicode e origem imutável; cópia editável sem modificar fonte. Testes de trilha com módulo/unidade/versão nos cadernos global e por tema; E2E com origem e recuperação após falha de rede. | Seleções de blocos visuais têm representação textual própria no painel de recorte. |
| 08/11/2026 | B015 | CONCLUÍDO | Excalidraw 0.18.1 e .excalidraw/PNG aprovados pelo usuário; MIT e avisos de fontes preservados. E2E desenha forma, recarrega, recupera cena e confere JSON editável/assinatura PNG. Fontes locais; auditoria npm sem vulnerabilidades após overrides. | Desfazer/refazer é da sessão; não há histórico de todas as cenas. Auditoria completa comercial/de acessibilidade permanece futura. |
| 08/11/2026 | B013–B015 | CHECKS | Backend: pytest 48 passed, 3 skipped; Ruff check/format, mypy e pip check aprovados. Frontend: 11 testes unitários; format/lint/typecheck/build aprovados; E2E Edge 8 passed, 2 skipped. Capturas desktop/celular inspecionadas e largura 390 px sem rolagem horizontal. Contratos, ADR, planejamento e TASKS conciliados. Ver docs/development/milestone4-validation.md. | CI remoto, instalação limpa completa, banco pessoal e benchmark NÃO EXECUTADOS. Modelo real não foi chamado neste marco, pois o caderno não depende de IA. Commit/push NÃO EXECUTADOS. |

## Próxima ação recomendada

Após aprovação do Marco 5, iniciar **B016 — Flashcards e revisão espaçada**. Antes de usar o Marco 4 no banco pessoal, encerrar a API, fazer backup validado e aplicar Alembic até a revisão 0004 conforme o README. A escolha do quadro foi resolvida neste marco; a auditoria completa de distribuição permanece em B025.
