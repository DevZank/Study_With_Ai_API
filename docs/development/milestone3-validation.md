# Marco 3 — Registro de entrega e validação

Data: 08/11/2026. Escopo: B010, B011 e B012. Nenhuma dependência nova. Nenhuma funcionalidade do Marco 4 iniciada.

## Implementado

Plano editável sem aulas antecipadas; unidades geradas explicitamente; granularidade automática; cache e versões; cancelamento e recuperação; resumos persistidos; contexto limitado; progresso separado de domínio e retenção. As regras e limitações estão na [ADR 0004](../architecture/0004-incremental-trails.md) e os endpoints no [contrato HTTP](../api/contracts.md).

## Arquivos alterados ou adicionados

Backend:

- README.md, TASKS.md.
- alembic/env.py e alembic/versions/0003_trails.py.
- src/study_api/main.py.
- src/study_api/domain/chat.py e domain/trails.py.
- src/study_api/application/chat.py, structured.py, trail_service.py e trail_generation.py.
- src/study_api/infrastructure/db/models.py e db/trails.py.
- src/study_api/presentation/trails.py.
- tests/e2e_server.py, trail_fixture.py, test_trails.py, test_trail_context.py, test_trail_migration.py e test_real_trails.py.
- docs/api/contracts.md, docs/architecture/0004-incremental-trails.md e este registro.

Frontend (caminhos relativos à raiz do repositório frontend):

- README.md, TASKS.md.
- src/features/themes/Topics.tsx e src/styles/app.css.
- src/features/trails/api.ts, Trails.tsx, ModuleEditor.tsx e UnitReader.tsx.
- e2e/milestone3.e2e.ts.
- Cópias conciliadas de docs/api/contracts.md, docs/architecture/0004-incremental-trails.md e deste registro.

Na pasta de trabalho comum, TASKS.md também foi conciliado com o backend. AGENTS.md e o planejamento não precisaram de alterações.

## Verificado

Backend, pelo Python do ambiente virtual:

- `python -m pytest -q --tb=short`: **37 passed, 3 skipped**. Inclui atualização 0002→0003 com histórico existente, comparação de metadados, recuperação após reinício, cache sem nova chamada de conteúdo ao modelo, versões antigas, cancelamento, edição/reordenação/adição/arquivamento, conflito de revisão, rejeição de plano inválido, evidência de tentativa e orçamento de contexto. Os três testes reais opcionais ficam ignorados sem variável de ambiente.
- `STUDY_TEST_OLLAMA_MODEL=qwen3.5:4b` com `python -m pytest tests/test_real_trails.py -q -s --tb=short`: **1 passed em 137,90 s**. Cinco módulos reais, nenhum conteúdo antecipado; duas unidades geradas sob demanda e resumo da primeira usado na segunda. Somente Ollama local e dados sintéticos.
- Ruff check/format, mypy em src/tests e pip check: aprovados. A restrição de criação de pasta temporária na execução inicial foi resolvida executando testes com a permissão apropriada.

Frontend:

- `npm test`: **11 passed** em três arquivos.
- `npm run typecheck`, `npm run lint`, `npm run format:check` e `npm run build`: aprovados. O build mantém avisos de diretivas use client de dependência já presentes.
- `E2E_BASE_URL=http://127.0.0.1:15173` com `npm run test:e2e`: **5 passed, 2 skipped** no Edge. Inclui regressões dos Marcos 1/2 e o fluxo completo do Marco 3 com provedor determinístico identificado como e2e:local, exclusivo de testes. Testes de modelo real dos marcos anteriores ficam opcionais.
- Capturas marco3-desktop.png e marco3-mobile.png em test-results/ inspecionadas; largura de 390 px sem rolagem horizontal. Controles usam rótulos, botões nativos e foco do navegador. Não constitui auditoria completa de acessibilidade.

## Não verificado e riscos

- Banco pessoal, restauração de backup pessoal, CI remoto, instalação limpa e benchmark de GPU de 6 GB: **NÃO EXECUTADOS**.
- Validação real de trilha ocorreu pela API; o cenário de navegador usa o provedor determinístico de teste. Não foi executado E2E de trilha com modelo real no navegador.
- Conteúdo e gabaritos gerados por IA podem estar pedagogicamente incorretos. Não há estimativa de domínio ou retenção.
- A API requer uma instância/worker por banco. Interrupções entre persistência do resultado e confirmação do job podem deixar job interrupted com resultado recuperável; veja a ADR.
- Não foi feita migração, exclusão ou alteração dos dados pessoais. Commit e push não foram executados.

## Próximo incremento

Atualizar a instalação pessoal somente após backup validado e autorização aplicável para essa operação. O próximo desenvolvimento é B013, mediante aprovação do Marco 4; a escolha de desenho/licença permanece pendente para B015.
