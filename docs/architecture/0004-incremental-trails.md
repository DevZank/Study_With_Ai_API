# ADR 0004 — Trilhas e continuidade incremental (Marco 3)

Implementado em 08/11/2026 para B010–B012. Não acrescenta dependências.

## Plano e edição

O Ollama gera somente metadados: título, pré-requisitos e de um a oito módulos com objetivos, critérios, duração estimada e títulos de aulas. A gramática restringe a quantidade solicitada; Pydantic valida novamente antes de salvar. Nenhum conteúdo de unidade é criado nesta etapa.

O usuário pode renomear a trilha, editar objetivos/critério/título de módulos, adicionar, arquivar, restaurar e reordenar módulos. Edições exigem expected_version e atualização condicional no banco; conflitos retornam 409. Não há edição durante uma operação da mesma trilha. Arquivar preserva conteúdo e histórico; restaurar acrescenta o módulo ao final. A edição de metadados preserva a divisão de unidades já existente: uma divisão diferente requer adicionar um módulo.

## Geração e versões

A política inicial divide em aulas quando a estimativa supera 25 minutos ou há mais de três objetivos; caso contrário, o módulo constitui uma unidade curta. É uma heurística de organização, sem promessa de duração real ou adequação pedagógica. A decisão é apresentada na UI e fica estável após o planejamento.

Abrir uma unidade permite navegar livremente. Gerar exige ação explícita e cria somente a unidade solicitada. O conteúdo usa a validação de blocos do Marco 2, exigindo explicação e exercício. Conversas internas com origin=trail não aparecem no estudo livre. O contrato de mensagens existente permanece compatível.

Uma versão existente é devolvida pelo cache sem gerar conteúdo novamente. force_regenerate=true cria uma nova versão, até dez por unidade, preservando mensagens, exercícios, tentativas e resumos anteriores. Cada versão registra revisão do plano, modelo e snapshot do contexto. Mudanças no plano ou no contexto sinalizam conteúdo anterior; não há atualização silenciosa.

## Persistência e operações

A migração aditiva 0003 cria trails, trail_modules, lessons, lesson_versions, learning_summaries e trail_jobs, além de conversations.origin. Metadados de cada agregado são JSON validado; IDs, proprietário, referências, revisão e índices necessários permanecem relacionais. Não há importação de código entre repositórios.

Jobs de trilha têm namespace próprio /trail-jobs para preservar /jobs do chat, duas operações concorrentes no processo e apenas uma ativa por alvo no SQLite. Possuem idempotência, cancelamento, timeout de 200 segundos e recuperação conservadora como interrupted após reinício. A UI usa polling; há SSE de snapshots de estado, sem JSON bruto do modelo. Cancelar a geração de unidade também cancela seu job interno.

Documento e exercícios são confirmados juntos pelo fluxo existente; versão/resumo e confirmação do job de trilha são transações separadas. Uma interrupção entre elas pode deixar resultado persistido com job interrupted. A leitura e a repetição pelo cache permitem recuperar dados sem alegar conclusão da operação interrompida. A instalação continua exigindo uma única instância/worker por banco.

## Resumos e indicadores

Concluir uma versão gera conceitos, conclusões e próximos passos validados. As dificuldades são texto informado pelo aluno, preservado sem reescrita pela IA. O resumo registra contagens reais de tentativas objetivas e acertos segundo o gabarito do modelo; não certifica conhecimento. O resumo usa um trecho público de até 4.000 caracteres e essas contagens, sem respostas privadas ou gabaritos não tentados. A conclusão é explícita e não exige acerto para permitir navegação livre.

Cada versão tem um resumo de conclusão imutável. Repetir com as mesmas dificuldades reutiliza o resumo; alterações retornam SUMMARY_EXISTS. Tentativas posteriores não alteram retroativamente a evidência registrada. Outra versão pode ter sua própria conclusão.

A unidade seguinte recebe somente os últimos três resumos disponíveis de unidades anteriores ativas na ordem atual, reduzidos por remoção dos mais antigos até 4.500 caracteres na lista serializada. O prompt completo tem limite explícito de 11.000 caracteres. Não se usa histórico bruto das outras unidades; exceder metadados gera erro, sem truncamento silencioso. O snapshot identifica resumos usados e quantidade omitida. Esses limites são de caracteres, não uma garantia de contagem exata de tokens.

O progresso conta a conclusão da versão mais recente das unidades ativas. Regenerar preserva a conclusão antiga, mas a versão atual ainda precisa ser concluída. Domínio e retenção permanecem não estimados; B017 depende de métricas pedagógicas próprias.

## Operação e limitações

Antes de atualizar banco pessoal: encerrar a API, copiar a pasta de dados e arquivos SQLite auxiliares e validar a restauração. Depois aplicar Alembic até head. Downgrade destrutivo é bloqueado; reverter requer o backup e a versão anterior do aplicativo. Esta entrega testa somente bancos temporários, sem migrar os dados pessoais.

Ollama local é o único destino. Não há pesquisa web, envio externo, geração automática de aulas futuras ou funções de marcos posteriores. A validade estrutural não garante correção pedagógica. O teste real com qwen3.5:4b não constitui benchmark de hardware de 6 GB de VRAM.
