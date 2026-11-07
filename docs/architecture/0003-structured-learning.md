# ADR 0003 — Modos, blocos e exercícios (Marco 2)

Aceito em 07/11/2026 para B007–B009.

## Contratos e compatibilidade

O contrato público de conteúdo tem schema_version 1.0 e está em docs/api/content-v1.schema.json. A exportação vem de PublicDocument: nunca exportar o schema privado de geração com gabaritos para a API ou o frontend. O script scripts/export_content_schema.py atualiza o arquivo do backend; a cópia no frontend deve ser conciliada explicitamente entre repositórios.

A API continua em /api/v1. Mensagens antigas permanecem textuais; a migração 0002 adiciona colunas com defaults e tabelas de exercícios/tentativas, sem remover conteúdo. Clientes antigos podem continuar enviando texto no formato anterior. A interface nova solicita response_format=blocks. Praticar exige esse formato para impedir que o fluxo legado exponha um gabarito de exercício como texto.

O modo ativo é persistido por conversa, e cada mensagem registra o modo usado. Trocar de modo mantém tema e histórico. Não é permitido trocar durante geração ativa. O roteamento de modelos permanece manual e local, conforme o Marco 1.

## Validação e exposição de dados

Os blocos são uniões discriminadas por type, com campos permitidos e limites de tamanho, quantidade e referências. São suportados texto, explicação, exemplo, código, fórmula, tabela, comparação, cartão de recuperação, questão de reflexão, quiz/exercício, dica, resumo, linha do tempo, diagrama, curiosidade e aviso de origem. O aviso de origem declara conhecimento do modelo sem consulta externa; não se geram citações fictícias.

O Ollama recebe uma gramática específica do modo. Memorizar gera cartões e Praticar gera exercícios; o modo é fixado no schema da requisição. A validação final continua obrigatória, pois a gramática não garante invariantes pedagógicos ou relacionais. Uma resposta inválida pode ser gerada novamente uma única vez, dentro do tempo máximo de geração. Os logs registram tipos de erro e IDs, sem conteúdo.

Durante geração estruturada, o JSON bruto fica apenas na memória do backend: pode conter respostas corretas. Nenhum delta bruto é enviado no SSE ou salvo no histórico público. A interface acompanha o job e aguarda os blocos validados. Cancelamento/falha descarta o rascunho não validado e preserva a pergunta e os estados. O streaming textual legado continua preservando texto parcial.

Depois da validação, o documento público recebe referências UUID de exercícios. O gabarito, a explicação e as dicas ficam na tabela privada de exercícios. Documento, exercícios e confirmação do job são gravados na mesma transação. Uma falha nessa transação não pode publicar uma resposta concluída com referências inexistentes.

A proteção é estrutural: campos de gabarito não são enviados antes da tentativa. Não certifica a correção pedagógica do conteúdo ou das pistas geradas por um modelo.

## Correção e tentativas

Múltipla escolha compara IDs de alternativas; verdadeiro/falso usa true/false; lacunas comparam texto normalizado em Unicode NFKC, sem distinguir maiúsculas/minúsculas e espaços redundantes. Não há avaliação aproximada, execução de código ou equivalência semântica inventada.

Questões abertas registram a resposta e mostram uma referência para revisão após a tentativa, sem nota automática. Esse estado é explícito na interface. Dicas são reveladas progressivamente, com contador persistido. Tentativas têm chave de idempotência e sobrevivem à recarga/reabertura do banco. Depois de pelo menos uma tentativa, o backend permite consultar a referência do exercício.

O frontend informa que o gabarito é gerado por IA e pode conter erros. Notas objetivas são comparação com esse gabarito, não estimativa de domínio, retenção ou XP. Agendamento FSRS e métricas continuam fora do Marco 2.

## Renderização e segurança

A UI valida os blocos e escolhe componentes permitidos. Documentos de versão desconhecida e blocos inválidos têm fallback sem interpretar ou imprimir JSON arbitrário. Código aparece como texto, sem botão de execução. Diagramas usam nós e arestas limitados, sem scripts Mermaid ou SVG fornecido pelo modelo.

Fórmulas usam KaTeX 0.19.1 com trust=false, strict=error, limite de expansão 100, limite de tamanho 10 e entrada de até 1000 caracteres. Somente o markup produzido por esse parser local chega ao componente de fórmula; erros mostram a expressão como texto escapado. A licença MIT foi conferida no pacote instalado; @types/katex 0.16.8 também declara MIT. Não foram acrescentadas dependências Python.

A primeira validação real rejeitou um documento de Memorizar. Após restringir a gramática por modo, os quatro modos produziram documentos válidos com qwen3.5:4b. Isso não é benchmark nem recomendação para GPU de 6 GB.

Fontes consultadas via Context7: [uniões Pydantic](https://docs.pydantic.dev/latest/concepts/unions/), [saídas estruturadas Ollama](https://github.com/ollama/ollama/blob/main/docs/capabilities/structured-outputs.mdx) e [segurança KaTeX](https://katex.org/docs/security.html).

