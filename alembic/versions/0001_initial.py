"""Cria a persistência inicial sem alterar bancos existentes fora da revisão."""

import sqlalchemy as sa

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "profiles",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("display_name", sa.String(), nullable=False),
    )
    op.bulk_insert(
        sa.table("profiles", sa.column("id"), sa.column("display_name")),
        [
            {
                "id": "00000000-0000-0000-0000-000000000001",
                "display_name": "Perfil local",
            }
        ],
    )
    for name, columns, constraints in [
        (
            "topics",
            [
                sa.Column("title", sa.String(120), nullable=False),
                sa.Column("status", sa.String(), nullable=False),
            ],
            [sa.CheckConstraint("status IN ('active','archived','deleted')")],
        ),
        (
            "conversations",
            [
                sa.Column(
                    "topic_id",
                    sa.String(36),
                    sa.ForeignKey("topics.id"),
                    nullable=False,
                ),
                sa.Column("title", sa.String(), nullable=False),
            ],
            [],
        ),
        (
            "messages",
            [
                sa.Column(
                    "conversation_id",
                    sa.String(36),
                    sa.ForeignKey("conversations.id"),
                    nullable=False,
                ),
                sa.Column("role", sa.String(), nullable=False),
                sa.Column("content", sa.Text(), nullable=False),
                sa.Column("model_id", sa.String(), nullable=False),
                sa.Column("status", sa.String(), nullable=False),
            ],
            [
                sa.CheckConstraint("role IN ('user','assistant')"),
                sa.CheckConstraint(
                    "status IN ('running','completed','failed','cancelled','interrupted')"
                ),
            ],
        ),
        (
            "generation_jobs",
            [
                sa.Column(
                    "conversation_id",
                    sa.String(36),
                    sa.ForeignKey("conversations.id"),
                    nullable=False,
                ),
                sa.Column(
                    "message_id",
                    sa.String(36),
                    sa.ForeignKey("messages.id"),
                    nullable=False,
                ),
                sa.Column("model_id", sa.String(), nullable=False),
                sa.Column("request_id", sa.String(36), nullable=False, unique=True),
                sa.Column("request_hash", sa.String(), nullable=False),
                sa.Column("status", sa.String(), nullable=False),
                sa.Column("error_code", sa.String(), nullable=False),
                sa.Column("error_message", sa.String(), nullable=False),
            ],
            [
                sa.CheckConstraint(
                    "status IN ('running','completed','failed','cancelled','interrupted')"
                )
            ],
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
        if name != "topics":
            key = "topic_id" if name == "conversations" else "conversation_id"
            op.create_index(f"ix_{name}_{key}", name, [key])
    op.create_index(
        "one_running_job",
        "generation_jobs",
        ["conversation_id"],
        unique=True,
        sqlite_where=sa.text("status = 'running'"),
    )


def downgrade() -> None:
    raise RuntimeError(
        "Reversão destrutiva desabilitada. Restaure um backup validado após confirmação."
    )
