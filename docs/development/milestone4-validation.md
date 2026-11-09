# Marco 4 — Registro de entrega e validação

Data: 08/11/2026. Escopo aprovado: B013–B015. Excalidraw e exportações `.excalidraw`/PNG foram aprovados pelo responsável nesta sessão. Nenhuma funcionalidade do Marco 5 foi iniciada.

## Implementado

Cadernos globais, por tema e vinculados a trilhas; pastas hierárquicas; páginas com texto rico; tags, busca, vínculos e movimentação sem duplicação. Autosave com versões e rascunhos locais; conflitos preservam o conteúdo para conciliação. Recortes editáveis mantêm origem imutável, incluindo módulo/unidade/versão de trilha. Quadro Excalidraw local com cena editável, recuperação e exportação de JSON/PNG.

## Arquivos alterados ou adicionados

Backend, relativos à raiz de seu repositório:

- README.md, TASKS.md e PLANEJAMENTO_PLATAFORMA_ESTUDOS_IA.md.
- alembic/env.py e alembic/versions/0004_notebooks.py.
- src/study_api/main.py.
- src/study_api/domain/notebooks.py.
- src/study_api/application/notebooks.py.
- src/study_api/infrastructure/db/notebooks.py.
- src/study_api/presentation/notebooks.py.
- tests/test_notebooks.py.
- docs/api/contracts.md, docs/architecture/0005-local-notebooks.md e este registro.

Frontend, relativos à raiz de seu repositório:

- README.md, TASKS.md, PLANEJAMENTO_PLATAFORMA_ESTUDOS_IA.md e .gitignore.
- package.json, package-lock.json e tsconfig.json.
- scripts/copy-editor-assets.mjs e src/types/excalidraw-locale.d.ts.
- src/features/notebooks/api.ts, Notebooks.tsx, PageEditor.tsx, RichEditor.tsx, DrawingBoard.tsx, ClippingCapture.tsx e use-autosave.ts.
- src/features/themes/Topics.tsx, src/features/chat/Chat.tsx e src/features/trails/UnitReader.tsx.
- src/styles/app.css e e2e/milestone4.e2e.ts.
- docs/licenses/README.md e avisos originais dos editores/fontes em .txt.
- Cópias conciliadas de docs/api/contracts.md, docs/architecture/0005-local-notebooks.md e deste registro.

Na pasta de trabalho comum: TASKS.md e o planejamento foram conciliados com o backend. AGENTS.md não foi alterado. Recursos de fontes são gerados pelo postinstall em public/excalidraw, ignorados pelo Git e incluídos no build junto com os avisos de licença.

## Verificado

Backend, pelo Python do ambiente virtual:

- Antes das alterações: `python -m pytest -q --tb=short`: **37 passed, 3 skipped**.
- Entrega: `python -m pytest -q --tb=short`: **48 passed, 3 skipped**. Bancos temporários, migração/compatibilidade de metadados, regressões dos marcos anteriores, cadernos, edição/movimentação, ciclos de pastas, conflitos, idempotência, recorte global e por tema/trilha com origem, rejeição de conteúdo não permitido e recuperação após reiniciar a aplicação.
- `python -m ruff check .`, `python -m ruff format --check .`, `python -m mypy src tests` e `python -m pip check`: aprovados.
- Não foram acrescentadas dependências Python.

Frontend:

- `npm test`: **11 passed** em três arquivos.
- `npm run format:check`, `npm run typecheck`, `npm run lint` e `npm run build`: aprovados.
- `E2E_BASE_URL=http://127.0.0.1:15173` com `npm run test:e2e`: **8 passed, 2 skipped**, em Edge, com API local de testes e banco temporário. Os três novos cenários conferem texto rico/pasta/desenho/exportações, movimento/busca/vínculos e recorte/origem/rascunho após falha de rede.
- A exportação editável foi lida como JSON contendo elementos, e o PNG foi conferido pela assinatura de arquivo. O desenho de uma forma permaneceu após recarga.
- Capturas marco4-desktop.png e marco4-mobile.png em test-results/ inspecionadas. Largura de 390 px sem rolagem horizontal; o quadro oferece controles nativos para recentralizar o conteúdo em telas menores.
- `npm audit --omit=dev`: **zero vulnerabilidades**; a instalação final também reportou zero no conjunto auditado. Overrides e justificativas em docs/licenses/README.md e na ADR 0005. `npm ls --depth=0` confirmou as versões principais.
- `node scripts/copy-editor-assets.mjs` e build: fontes e avisos locais presentes em dist/excalidraw; verificada a existência de dist/excalidraw/licenses/excalidraw-MIT.txt.

Os primeiros E2E localizaram um seletor que tentava clicar no input coberto pelo ícone do Excalidraw e uma seleção de recorte que era limpa ao clicar em campos. O seletor foi corrigido para o controle visual nativo, e a captura passou a ignorar controles de formulário e seleções vazias. As execuções finais passaram. Uma execução simultânea interferiu nos arquivos de trace; a validação final foi executada sozinha.

O Edge recebe requisições injetadas pelo antivírus instalado na máquina. O teste de recursos locais distingue explicitamente esse tráfego da aplicação, sem alterar ou desativar o antivírus. Não foram observadas requisições externas da aplicação no fluxo do quadro; as fontes são locais. Os cenários de chat usam o provedor determinístico identificado como e2e:local, exclusivo de testes.

## Não verificado

- CI remoto, instalação limpa completa em outra máquina, banco pessoal, restauração de backup pessoal, outros sistemas/navegadores e benchmark de GPU: **NÃO EXECUTADOS**.
- Testes opcionais com modelo real: **NÃO EXECUTADOS neste marco**; o caderno não chama IA. Permanecem as evidências dos marcos anteriores.
- Auditoria completa de acessibilidade e verificação individual de todas as ferramentas nativas do canvas: **NÃO EXECUTADAS**. Foram exercitados desenho de forma, recuperação e exportação, e inspecionados os controles integrados.
- Commit e push: **NÃO EXECUTADOS**.

## Riscos e limites

Rascunhos dependem do localStorage e podem ser removidos pelo usuário/navegador; erros de armazenamento são informados. Não substituem backup. O histórico de texto conserva revisões, mas o desenho mantém apenas a cena atual com concorrência controlada e desfazer/refazer da sessão. Os limites de documento, cena e imagens estão na ADR e no contrato.

Excalidraw aumenta o tamanho do build; seu carregamento ocorre somente ao abrir o quadro. O build mantém avisos de diretivas use client de dependências e de tamanho de chunks. A auditoria completa de licenças/distribuição permanece em B025. Não há anexos gerais, importação de caderno nem backup global de B024 nesta entrega.

## Próximo incremento

Para uso pessoal, primeiro encerrar a API, fazer backup validado e aplicar Alembic até 0004, conforme README. O próximo desenvolvimento é B016, após aprovação do Marco 5.
