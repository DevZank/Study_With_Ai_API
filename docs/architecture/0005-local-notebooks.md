# ADR 0005 — Caderno local, recortes e desenho (Marco 4)

Escopo: B013–B015. O responsável aprovou Excalidraw e exportação `.excalidraw`/PNG nesta sessão. O editor TipTap já estava previsto no planejamento. Nenhuma funcionalidade dos Marcos 5–8 é antecipada.

## Cadernos, páginas e histórico

Cadernos são globais ou vinculados a um tema e, opcionalmente, a uma trilha desse tema. Pastas pertencem a um único caderno, aceitam subpastas e não admitem ciclos. Páginas têm um caderno de armazenamento e podem ter vários temas relacionados e vínculos para outras páginas, sem duplicar seu conteúdo. Movimentar uma página conserva seu ID, desenho, histórico e recortes. Alterações de conteúdo e organização são validadas pelo backend.

A migração aditiva 0004 cria notebooks, notebook_folders, notebook_pages, notebook_revisions, saved_clippings e drawing_boards. Cada registro tem proprietário local, versão e metadados validados em JSON. IDs e relações estruturais ficam também em colunas relacionais com chaves estrangeiras e índices. Não há exclusão física nesta entrega. Cadernos de temas na lixeira ficam ocultos até a restauração; os de temas arquivados podem ser lidos, mas alterações são rejeitadas.

Salvamentos usam expected_version e operation_id. A atualização condicional da versão evita sobrescrever outra edição; um conflito retorna 409. Cada edição de página guarda um snapshot na mesma transação. A API apresenta as 30 revisões mais recentes; recuperar uma revisão gera outra edição, preservando as anteriores. O desenho tem contador próprio de versão, separado do texto. Não há histórico de todas as cenas antigas: desfazer/refazer funciona na sessão do editor; a cena corrente é recuperada após recarga.

## Editor rico e segurança

TipTap 3.33.0 com StarterKit e TableKit: parágrafos, títulos, negrito, itálico, listas, código, tabelas e links. Uma extensão local de fórmula usa o renderer seguro de KaTeX já existente. Código não é executado. Colagens entram como texto para impedir incorporação de HTML externo. Imagens locais pertencem ao quadro; não há upload genérico de anexos neste marco.

O backend aceita somente nós, marcas e atributos permitidos, com validação de hierarquia, links e limites. Limites iniciais: 3.000 nós, 16 níveis e 250.000 caracteres de JSON por documento. Links aceitam http/https/mailto e rotas internas de caderno; javascript e nós HTML/imagem remota são rejeitados. Documentos são JSON versionado, sem HTML arbitrário persistido. Os serviços de caderno nunca chamam um provedor de IA.

## Salvamento e recuperação

O texto e o desenho usam autosave serializado a cada segundo. Um rascunho é guardado no localStorage do navegador antes do envio; não há telemetria nem envio externo desse conteúdo. O estado distingue pendente, salvando, salvo e erro. Falha de rede conserva o rascunho e exige nova tentativa ou recuperação após recarga. Se a versão do banco mudou, a recuperação interrompe o envio e permite exportar o rascunho para conciliação. A versão do banco só substitui o rascunho após confirmação explícita.

Há aviso ao fechar com conteúdo pendente. Quando o navegador não consegue guardar o rascunho, a interface informa a falha e protege a navegação por links da aplicação com confirmação. O rascunho continua sujeito a limites, limpeza e políticas de armazenamento do navegador; não substitui backup. Não foi implementado backup/restauração global de B024.

## Recortes com origem

Respostas concluídas de IA, tanto do estudo livre quanto de unidades da trilha, permitem selecionar um trecho e escolher um caderno/página ou criar uma nova página. O painel oferece também uma representação textual da resposta para selecionar trechos de blocos visuais.

O backend constrói a origem exclusivamente de dados persistidos: tema, conversa, mensagem, data, modelo e, quando disponível, trilha/módulo/unidade/versão. O intervalo é definido em pontos de código Unicode nessa representação textual, e seu conteúdo deve coincidir exatamente com selected_text. Não são offsets de HTML/DOM. Texto selecionado diretamente na apresentação é localizado no texto canônico; para desambiguar repetições, a seleção no painel textual preserva seu offset exato.

O documento recebe uma cópia editável, enquanto saved_clippings mantém trecho, intervalo e origem imutáveis. A transação reúne edição, revisão e recorte, com idempotência para evitar duplicação em repetição de envio. Editar a cópia não modifica a resposta original. O painel de origem oferece um link para a conversa ou a versão da unidade. A representação usa somente conteúdo público e enunciados, sem gabaritos ou soluções privadas de exercícios.

## Quadro e dependências

Excalidraw 0.18.1 é carregado apenas ao abrir o quadro. A integração mantém ferramentas de desenho, formas, setas, texto, seleção, cores, zoom/pan e desfazer/refazer. A cena atual inclui elementos, imagens locais e apenas fundo/posição/zoom do estado. Colaboradores, credenciais, bibliotecas remotas e estado transitório não são persistidos. IA e colaboração ficam desativadas; embeds e abertura de links no quadro são bloqueados. O menu é reduzido para preservar o salvamento pela aplicação.

O backend limita 2.000 elementos, 20.000 pontos por traço, dez imagens PNG/JPEG/WebP de até 500 KB cada e 2,5 MB por cena. O limite HTTP sobe para 3 MB somente em rotas de caderno/página; as rotas anteriores mantêm 32 KB. Requisições grandes continuam rejeitadas antes da API.

Exportar `.excalidraw` preserva elementos editáveis; PNG é uma imagem rasterizada, limitada a 4.096 pixels na maior dimensão. A importação geral de arquivos e o backup de instalação permanecem fora deste marco. As fontes são copiadas do pacote para public/excalidraw pelo postinstall, e a aplicação define EXCALIDRAW_ASSET_PATH para servir localmente, sem CDN.

As bibliotecas principais declaram MIT. Avisos oficiais de copyright/licença dos editores e fontes estão no frontend em docs/licenses e são conservados na distribuição. Excalifont, Assistant, Cascadia, Liberation, Lilita, Nunito e Xiaolai usam SIL OFL; ComicShanns possui aviso MIT nos metadados. Virgil está na árvore do Excalidraw sob a licença MIT do projeto, sem aviso separado na versão consultada. As licenças permitem uso comercial respeitando seus avisos e condições; isso não define a licença do código da plataforma. A auditoria completa de distribuição permanece em B025.

O pacote Excalidraw fixa dependências antigas. Overrides explícitos de nanoid, lodash-es, KaTeX e Radix Tabs corrigem alertas npm e compatibilidade declarada com React 19. A integração é conferida com build e navegador, sem aplicar npm audit fix --force. Mapeamentos de tipos apontam para declarações que existem no pacote, mas não são resolvidas pelos exports publicados. Um arquivo de declaração cobre a referência ausente de locale; strict continua ativo e skipLibCheck não foi habilitado.

## Atualização e riscos

Antes de atualizar banco pessoal: encerrar a API, copiar a pasta de dados com arquivos SQLite auxiliares e validar a restauração; só então aplicar Alembic até 0004. A entrega valida bancos temporários. O downgrade destrutivo continua bloqueado. Não há migração automática dos dados pessoais.

Busca atual usa título, texto serializado e tags das páginas do caderno; FTS/material/RAG pertencem a B019. A interface de desenho em celular é mais limitada pelo espaço e usa o controle nativo para recentralizar conteúdo. Auditoria completa de acessibilidade, desempenho com milhares de páginas e compatibilidade em outros sistemas não foi realizada neste marco.
