"""Acrescenta trilhas, unidades versionadas, resumos e jobs sem remover dados."""

import sqlalchemy as sa

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column("origin", sa.String(), nullable=False, server_default="free"),
    )
    tables = [
        (
            "trails",
            [
                sa.Column(
                    "topic_id",
                    sa.String(36),
                    sa.ForeignKey("topics.id"),
                    nullable=False,
                ),
                sa.Column("version", sa.Integer(), nullable=False),
            ],
            "topic_id",
        ),
        (
            "trail_modules",
            [
                sa.Column(
                    "trail_id",
                    sa.String(36),
                    sa.ForeignKey("trails.id"),
                    nullable=False,
                )
            ],
            "trail_id",
        ),
        (
            "lessons",
            [
                sa.Column(
                    "module_id",
                    sa.String(36),
                    sa.ForeignKey("trail_modules.id"),
                    nullable=False,
                )
            ],
            "module_id",
        ),
        (
            "lesson_versions",
            [
                sa.Column(
                    "unit_id",
                    sa.String(36),
                    sa.ForeignKey("lessons.id"),
                    nullable=False,
                ),
                sa.Column(
                    "message_id",
                    sa.String(36),
                    sa.ForeignKey("messages.id"),
                    nullable=False,
                ),
            ],
            "unit_id",
        ),
        (
            "learning_summaries",
            [
                sa.Column(
                    "version_id",
                    sa.String(36),
                    sa.ForeignKey("lesson_versions.id"),
                    nullable=False,
                )
            ],
            "version_id",
        ),
        (
            "trail_jobs",
            [
                sa.Column("target_id", sa.String(36), nullable=False),
                sa.Column("request_id", sa.String(36), unique=True, nullable=False),
                sa.Column("status", sa.String(), nullable=False),
            ],
            None,
        ),
    ]
    for name, columns, parent in tables:
        op.create_table(
            name,
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column(
                "owner_id", sa.String(), sa.ForeignKey("profiles.id"), nullable=False
            ),
            sa.Column("created_at", sa.String(), nullable=False),
            sa.Column("updated_at", sa.String(), nullable=False),
            sa.Column("data_json", sa.Text(), nullable=False),
            *columns,
        )
        op.create_index(f"ix_{name}_owner_id", name, ["owner_id"])
        if parent:
            op.create_index(f"ix_{name}_{parent}", name, [parent])
    op.create_index(
        "one_active_trail_target",
        "trail_jobs",
        ["target_id"],
        unique=True,
        sqlite_where=sa.text("status = 'running'"),
    )


def downgrade() -> None:
    raise RuntimeError(
        "Reversão destrutiva bloqueada. Restaure backup validado após confirmação."
    )
