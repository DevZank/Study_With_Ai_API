"""Acrescenta modos e exercícios, preservando o histórico textual existente."""

import sqlalchemy as sa

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column("active_mode", sa.String(), nullable=False, server_default="learn"),
    )
    for name, type_, default in [
        ("mode", sa.String(), "learn"),
        ("response_format", sa.String(), "text"),
        ("document_json", sa.Text(), ""),
        ("notice", sa.Text(), ""),
    ]:
        op.add_column(
            "messages", sa.Column(name, type_, nullable=False, server_default=default)
        )
    for name, columns, constraints in [
        (
            "exercises",
            [
                sa.Column(
                    "message_id",
                    sa.String(36),
                    sa.ForeignKey("messages.id"),
                    nullable=False,
                ),
                sa.Column("kind", sa.String(), nullable=False),
                sa.Column("prompt", sa.Text(), nullable=False),
                sa.Column("options_json", sa.Text(), nullable=False),
                sa.Column("answer_key", sa.Text(), nullable=False),
                sa.Column("explanation", sa.Text(), nullable=False),
                sa.Column("hints_json", sa.Text(), nullable=False),
                sa.Column(
                    "hints_revealed", sa.Integer(), nullable=False, server_default="0"
                ),
            ],
            [
                sa.CheckConstraint(
                    "kind IN ('multiple_choice','true_false','fill_blank','open')"
                )
            ],
        ),
        (
            "exercise_attempts",
            [
                sa.Column(
                    "exercise_id",
                    sa.String(36),
                    sa.ForeignKey("exercises.id"),
                    nullable=False,
                ),
                sa.Column("response", sa.Text(), nullable=False),
                sa.Column("request_id", sa.String(36), unique=True, nullable=False),
                sa.Column("score", sa.Float(), nullable=True),
                sa.Column("feedback", sa.Text(), nullable=False),
            ],
            [],
        ),
    ]:
        op.create_table(
            name,
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column(
                "owner_id", sa.String(), sa.ForeignKey("profiles.id"), nullable=False
            ),
            sa.Column("created_at", sa.String(), nullable=False),
            sa.Column("updated_at", sa.String(), nullable=False),
            *columns,
            *constraints,
        )
        op.create_index(f"ix_{name}_owner_id", name, ["owner_id"])
        parent = "message_id" if name == "exercises" else "exercise_id"
        op.create_index(f"ix_{name}_{parent}", name, [parent])


def downgrade() -> None:
    raise RuntimeError(
        "Reversão destrutiva bloqueada. Restaure um backup validado após confirmação."
    )
