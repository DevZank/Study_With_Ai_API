"""Adiciona tabelas de flashcards, revisão FSRS, métricas pedagógicas e gamificação."""

import sqlalchemy as sa

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def _base_columns() -> list[sa.Column[object]]:
    return [
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "owner_id", sa.String(), sa.ForeignKey("profiles.id"), nullable=False
        ),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.Column("updated_at", sa.String(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("data_json", sa.Text(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "concepts",
        *_base_columns(),
        sa.Column("topic_id", sa.String(), sa.ForeignKey("topics.id"), nullable=False),
        sa.Column("slug", sa.String(120), nullable=False),
    )
    op.create_index("ix_concepts_owner_id", "concepts", ["owner_id"])
    op.create_index("ix_concepts_topic_id", "concepts", ["topic_id"])

    op.create_table(
        "concept_mastery",
        *_base_columns(),
        sa.Column(
            "concept_id",
            sa.String(),
            sa.ForeignKey("concepts.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("topic_id", sa.String(), sa.ForeignKey("topics.id"), nullable=False),
    )
    op.create_index("ix_concept_mastery_owner_id", "concept_mastery", ["owner_id"])
    op.create_index("ix_concept_mastery_topic_id", "concept_mastery", ["topic_id"])

    op.create_table(
        "flashcards",
        *_base_columns(),
        sa.Column("topic_id", sa.String(), sa.ForeignKey("topics.id"), nullable=False),
        sa.Column(
            "concept_id", sa.String(), sa.ForeignKey("concepts.id"), nullable=True
        ),
        sa.Column("source_key", sa.String(120), nullable=True, unique=True),
        sa.Column("operation_id", sa.String(36), nullable=False, unique=True),
    )
    op.create_index("ix_flashcards_owner_id", "flashcards", ["owner_id"])
    op.create_index("ix_flashcards_topic_id", "flashcards", ["topic_id"])

    op.create_table(
        "review_states",
        *_base_columns(),
        sa.Column(
            "flashcard_id",
            sa.String(),
            sa.ForeignKey("flashcards.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("topic_id", sa.String(), sa.ForeignKey("topics.id"), nullable=False),
        sa.Column("due_at", sa.String(40), nullable=False),
    )
    op.create_index("ix_review_states_owner_id", "review_states", ["owner_id"])
    op.create_index("ix_review_states_topic_id", "review_states", ["topic_id"])
    op.create_index("ix_review_states_due_at", "review_states", ["due_at"])

    op.create_table(
        "review_events",
        *_base_columns(),
        sa.Column(
            "review_state_id",
            sa.String(),
            sa.ForeignKey("review_states.id"),
            nullable=False,
        ),
        sa.Column(
            "flashcard_id",
            sa.String(),
            sa.ForeignKey("flashcards.id"),
            nullable=False,
        ),
        sa.Column("request_id", sa.String(36), nullable=False, unique=True),
    )
    op.create_index("ix_review_events_owner_id", "review_events", ["owner_id"])
    op.create_index(
        "ix_review_events_review_state_id", "review_events", ["review_state_id"]
    )
    op.create_index("ix_review_events_flashcard_id", "review_events", ["flashcard_id"])

    op.create_table(
        "xp_events",
        *_base_columns(),
        sa.Column("topic_id", sa.String(), sa.ForeignKey("topics.id"), nullable=True),
        sa.Column("source_key", sa.String(120), nullable=False, unique=True),
    )
    op.create_index("ix_xp_events_owner_id", "xp_events", ["owner_id"])
    op.create_index("ix_xp_events_topic_id", "xp_events", ["topic_id"])

    op.create_table(
        "achievements",
        *_base_columns(),
        sa.Column("code", sa.String(64), nullable=False, unique=True),
    )
    op.create_index("ix_achievements_owner_id", "achievements", ["owner_id"])

    op.create_table(
        "earned_achievements",
        *_base_columns(),
        sa.Column(
            "achievement_id",
            sa.String(),
            sa.ForeignKey("achievements.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("code", sa.String(64), nullable=False, unique=True),
    )
    op.create_index(
        "ix_earned_achievements_owner_id", "earned_achievements", ["owner_id"]
    )

    op.create_table(
        "progress_preferences",
        *_base_columns(),
    )
    op.create_index(
        "ix_progress_preferences_owner_id", "progress_preferences", ["owner_id"]
    )


def downgrade() -> None:
    raise RuntimeError(
        "Reversão destrutiva bloqueada. Restaure um backup validado após confirmação."
    )

