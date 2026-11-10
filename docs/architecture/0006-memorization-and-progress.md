# ADR 0006 — Memorização espaçada FSRS, métricas pedagógicas e gamificação leve (Marco 5)

Escopo: B016–B018. Nenhuma funcionalidade dos Marcos 6–8 é antecipada. Não foram adicionadas dependências externas Python ou npm neste marco.

## Agendador determinístico FSRS e flashcards (B016)

Os cartões de memorização (`flashcards`) pertencem a um tema e podem ser:
- criados ou editados manualmente (`source_type = manual`);
- importados de um bloco `flashcard` validado de resposta concluída da IA (`source_type = message_block`), preservando `source_ref` (`message_id`, `block_id`, `conversation_id`, `model_id` e, quando aplicável, metadados da trilha/unidade).

A importação constrói `source_key = msg:{message_id}:{block_id}` com restrição de unicidade por proprietário local, evitando duplicação do mesmo cartão ao repetir a ação. O texto da frente e do verso é extraído exclusivamente do `document_json` persistido da mensagem concluída, sem chamar novamente o provedor de IA e sem aceitar texto de origem forjado pelo cliente.

Cada cartão possui uma linha correspondente em `review_states` e um histórico imutável em `review_events`. O agendador implementa a formulação determinística FSRS-4.5 no domínio (`study_api.domain.progress.schedule_review` e `retrievability_at`) com avaliações `1` (Errei), `2` (Difícil), `3` (Bom) e `4` (Fácil):
- Cartões novos iniciam em `state = new`, `due_at = created_at`, `stability = 0`, `difficulty = 0`, `reps = 0` e `lapses = 0`.
- A primeira revisão calcula estabilidade inicial $S_0(G)$ e dificuldade inicial $D_0(G) \in [1, 10]$.
- Revisões subsequentes calculam o tempo decorrido $\Delta t$, a recuperabilidade $R(\Delta t, S) = (1 + \frac{19}{81} \cdot \frac{\Delta t}{S})^{-0.5}$, a nova dificuldade com reversão à média e a nova estabilidade de recordação ($G \in \{2,3,4\}$) ou esquecimento ($G = 1$, incrementando `lapses` e transicionando para `relearning`).
- O próximo intervalo em dias é determinístico para a retenção-alvo de 90% ($R = 0.9 \implies I = \max(1, \text{round}(S))$) quando $G \in \{2,3,4\}$, ou 10 minutos em UTC quando $G = 1$.
- Todas as datas (`reviewed_at`, `due_at`) são persistidas em ISO-8601 UTC; informar o mesmo instante `reviewed_at` produz exatamente o mesmo estado e `due_at`, permitindo testes determinísticos e reprodutibilidade completa após reiniciar a aplicação.
- A avaliação exige `request_id` (UUID) com idempotência transacional em `review_events`.

## Indicadores pedagógicos estritamente separados (B017)

A plataforma calcula e exibe três indicadores distintos por tema e na visão geral (`GET /api/v1/progress/topics/{id}` e `GET /api/v1/progress/overview`), nunca fundidos em uma nota única:

1. **Progresso de conclusão (`completion`)**: unidades concluídas (`completed_units`) sobre o total de unidades planejadas (`total_units`) nas trilhas ativas do tema. Mede apenas avanço de leitura/etapas e não representa domínio nem retenção.
2. **Domínio estimado (`mastery`)**: calculado por conceito (`concepts` e `concept_mastery`) a partir de evidências reais persistidas:
   - tentativas em questões objetivas (`score` 0 ou 1 em `exercise_attempts`, peso 1,0);
   - revisões espaçadas FSRS (`review_count`, peso 0,6) dos cartões vinculados ao conceito.
   Quando não há tentativas nem revisões (`evidence_count = 0`), o domínio permanece `null` (`Não estimado`) com grau de incerteza `unestimated`. Todas as estimativas trazem explicação explícita (`explanations`) e grau de incerteza (`high`, `moderate`, `low`).
3. **Retenção estimada (`retention`)**: média da recuperabilidade FSRS $R(t, S)$ dos cartões já revisados ao menos uma vez (`reviewed_cards`), acompanhada de `due_cards` (cartões vencidos) e `active_cards`. Permanece `null` enquanto nenhum cartão tiver sido revisado.

As recomendações adaptativas (`recommendations`) sugerem próximos passos (`review_due`, `practice_concept`, `create_flashcards`, `advance_trail`, `keep_pace`), preservando a decisão final sempre com o usuário.

## Gamificação leve, ética e auditável (B018)

O sistema de gamificação registra cada ganho no razão auditável `xp_events`, com `source_key` única por proprietário para impedir ganhos repetitivos ou artificiais (anti-farming):
- `exercise_first_try`: +5 XP na primeira tentativa de cada exercício;
- `exercise_correct`: +15 XP na primeira resposta objetiva correta de cada exercício (repetir o mesmo exercício não gera XP adicional);
- `unit_completion`: +25 XP na primeira conclusão de cada unidade de trilha;
- `flashcard_review`: +10 XP apenas quando o cartão estava efetivamente vencido no instante da revisão (`was_due = true`), limitado a uma janela por cartão/dia e ao teto diário de 30 revisões pontuadas (`DAILY_REVIEW_XP_CAP = 30`). Revisar cartões adiantados atualiza o FSRS normalmente, mas concede `0 XP`.

O nível é derivado deterministicamente do XP acumulado (`100 * nível` por faixa). As conquistas iniciais (`first_practice`, `accurate_practice`, `first_review`, `ten_reviews`, `first_trail_unit`, `practice_and_review`) são desbloqueadas em transação quando os marcos reais são atingidos. O usuário pode ocultar ou reexibir toda a camada de gamificação a qualquer momento (`PATCH /api/v1/progress/preferences` com `hide_gamification = true/false`), sem afetar o registro em banco nem os indicadores pedagógicos.

## Migração e segurança

A migração aditiva `0005` cria `concepts`, `concept_mastery`, `flashcards`, `review_states`, `review_events`, `xp_events`, `achievements`, `earned_achievements` e `progress_preferences`. Para atualizar dados pessoais de marcos anteriores, encerre a API, faça backup validado da pasta de dados e aplique `alembic upgrade head`. O downgrade destrutivo continua bloqueado.
