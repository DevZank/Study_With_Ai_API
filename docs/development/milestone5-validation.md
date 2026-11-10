# Marco 5 — Registro de entrega e validação

Data: 10/11/2026. Escopo aprovado: B016–B018. Nenhuma funcionalidade dos Marcos 6–8 foi iniciada. Nenhuma dependência externa Python ou npm foi adicionada.

## Implementado

- **B016 — Flashcards e revisão espaçada**: criação e edição manual de flashcards com controle otimista de concorrência (`expected_version`) e idempotência (`operation_id`); importação de blocos `flashcard` de respostas estruturadas concluídas da IA (modo Memorizar e unidades de trilha) preservando a origem (`source_ref`) e impedindo duplicação do mesmo bloco (`source_key = msg:{message_id}:{block_id}`); agendador determinístico FSRS-4.5 no domínio (`schedule_review`, `retrievability_at`) com avaliações `1..4`, estabilidade, dificuldade, recuperabilidade, contagem de repetições/lapsos e datas de vencimento reproduzíveis em ISO-8601 UTC; fila de revisão vencida por tema e global; histórico imutável de eventos de revisão (`review_events`).
- **B017 — Métricas pedagógicas**: cálculo e apresentação estritamente separados de três indicadores: (1) **Progresso de conclusão** de unidades/trilhas (`completion`), (2) **Domínio estimado por conceito** (`mastery`) a partir de tentativas objetivas de exercícios e revisões FSRS com grau explícito de incerteza (`unestimated`, `high`, `moderate`, `low`), e (3) **Retenção estimada** (`retention`) pela curva de esquecimento FSRS dos cartões revisados; textos explicativos de cada indicador e sugestões pedagógicas adaptativas determinísticas onde o usuário sempre decide.
- **B018 — Gamificação leve**: razão auditável de XP (`xp_events`) com chave de unicidade (`source_key`) e proteção contra ganhos repetitivos ou artificiais (primeira tentativa de exercício, primeira resposta correta de exercício, conclusão de unidade e revisão FSRS apenas quando o cartão estava efetivamente vencido, com limite diário); cálculo determinístico de níveis; conquistas simples (`first_practice`, `accurate_practice`, `first_review`, `ten_reviews`, `first_trail_unit`, `practice_and_review`) e preferência persistida para ocultar ou exibir toda a camada de gamificação (`hide_gamification`).

## Arquivos alterados ou adicionados

Backend, relativos à raiz de seu repositório:

- `README.md`, `TASKS.md` e `PLANEJAMENTO_PLATAFORMA_ESTUDOS_IA.md`.
- `alembic/env.py` e `alembic/versions/0005_memorization_progress.py`.
- `src/study_api/main.py` e `src/study_api/presentation/exercises.py`.
- `src/study_api/domain/progress.py`.
- `src/study_api/application/progress.py`.
- `src/study_api/infrastructure/db/progress.py`.
- `src/study_api/presentation/progress.py`.
- `tests/test_progress.py` e `tests/test_trail_migration.py`.
- `docs/api/contracts.md`, `docs/architecture/0006-memorization-and-progress.md` e este registro.

Frontend, relativos à raiz de seu repositório:

- `README.md`, `TASKS.md` e `PLANEJAMENTO_PLATAFORMA_ESTUDOS_IA.md`.
- `src/features/progress/api.ts`, `src/features/progress/Memorize.tsx` e `src/features/progress/Progress.tsx`.
- `src/features/content/Blocks.tsx`, `src/features/chat/Chat.tsx`, `src/features/trails/Trails.tsx`, `src/features/trails/UnitReader.tsx`, `src/features/exercises/ExerciseCard.tsx` e `src/features/themes/Topics.tsx`.
- `src/styles/app.css`, `tests/api.test.ts` e `e2e/milestone5.e2e.ts`.
- Cópias conciliadas de `docs/api/contracts.md`, `docs/architecture/0006-memorization-and-progress.md` e deste registro.

Na pasta de trabalho comum (`d:\QUATTRO`): `TASKS.md` e `PLANEJAMENTO_PLATAFORMA_ESTUDOS_IA.md` foram conciliados com o backend. `AGENTS.md` não foi alterado.

## Verificado

Backend, pelo Python do ambiente virtual:

- `.\.venv\Scripts\python.exe -m pytest -q --tb=short`: **51 passed, 3 skipped**. Cobre agendamento determinístico FSRS e reprodutibilidade de datas de vencimento, migração `0004`→`0005` e compatibilidade de metadados SQLAlchemy/Alembic, criação/edição/importação de flashcards com origem, fila de revisão vencida, persistência após reiniciar a aplicação, separação estrita entre conclusão, domínio por conceito e retenção FSRS, proteção anti-farming de XP, conquistas e preferência de ocultar gamificação, além de todas as regressões dos Marcos 0–4.
- `.\.venv\Scripts\ruff.exe check .`, `.\.venv\Scripts\ruff.exe format --check .`, `.\.venv\Scripts\python.exe -m mypy src tests` e `.\.venv\Scripts\python.exe -m pip check`: aprovados sem erros.

Frontend:

- `npm test`: **12 passed** em três arquivos (`tests/health.test.ts`, `tests/api.test.ts`, `tests/content.test.tsx`).
- `npm run format:check`, `npm run lint`, `npm run typecheck` e `npm run build`: aprovados.
- `E2E_BASE_URL=http://127.0.0.1:15173` com `npm run test:e2e`: **9 passed, 2 skipped**, em Microsoft Edge, com API local de testes e banco SQLite temporário. O cenário `e2e/milestone5.e2e.ts` valida importação de flashcard gerado no modo Memorizar, resolução de exercício objetivo no modo Praticar, avaliação FSRS na fila de revisão vencida, criação e edição manual de cartão, histórico de revisão, persistência após recarregar a página, painel com os três indicadores pedagógicos separados, tabela de domínio por conceito, recomendações adaptativas, gamificação opcional (ocultar/exibir persistido após recarga) e visão geral de revisões e progresso.
- Capturas `test-results/marco5-desktop.png` (1280×800) e `test-results/marco5-mobile.png` (390×844) inspecionadas e sem rolagem horizontal (`scrollWidth <= innerWidth`).

## Não verificado

- CI remoto, instalação limpa completa em outra máquina, migração do banco pessoal (`Backend/data/study.sqlite3`), restauração de backup pessoal, outros sistemas/navegadores e benchmark de GPU de 6 GB: **NÃO EXECUTADOS**.
- Testes opcionais com modelo real (`STUDY_TEST_OLLAMA_MODEL` / `E2E_REAL_MODEL`): **NÃO EXECUTADOS neste marco**; o agendador FSRS, o cálculo de métricas e a gamificação são determinísticos e operam sobre eventos persistidos. Permanecem as evidências reais dos marcos anteriores.
- Commit e push: **NÃO EXECUTADOS**.

## Riscos e limites

O domínio estimado por conceito e a retenção estimada por FSRS são indicadores estatísticos/heurísticos sujeitos a incerteza e à qualidade dos gabaritos gerados por IA; não constituem certificação formal de aprendizado. Questões abertas não recebem nota automática e exigem revisão do próprio estudante. Revisar cartões antes do vencimento atualiza o estado FSRS, mas não concede XP para evitar ganhos artificiais.

## Próximo incremento

Para uso pessoal, primeiro encerrar a API, fazer backup validado da pasta de dados e aplicar Alembic até a revisão `0005`, conforme o README. O próximo desenvolvimento previsto é o **Marco 6 — Materiais e fontes (B019–B020)**, condicionado à definição do provedor de pesquisa web (D005) para B020.

