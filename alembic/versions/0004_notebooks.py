"""Adiciona cadernos e histórico sem excluir ou alterar conteúdo anterior."""

import sqlalchemy as sa

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for name, refs, unique in [
        (
            "notebooks",
            [("topic_id", "topics", True), ("trail_id", "trails", True)],
            None,
        ),
        (
            "notebook_folders",
            [
                ("notebook_id", "notebooks", False),
                ("parent_id", "notebook_folders", True),
            ],
            None,
        ),
        (
            "notebook_pages",
            [
                ("notebook_id", "notebooks", False),
                ("folder_id", "notebook_folders", True),
            ],
            None,
        ),
        ("notebook_revisions", [("page_id", "notebook_pages", False)], "operation_id"),
        (
            "saved_clippings",
            [("page_id", "notebook_pages", False), ("message_id", "messages", False)],
            "operation_id",
        ),
        ("drawing_boards", [("page_id", "notebook_pages", False)], "page_id"),
    ]:
        op.create_table(
            name,
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column(
                "owner_id", sa.String(), sa.ForeignKey("profiles.id"), nullable=False
            ),
            sa.Column("created_at", sa.String(), nullable=False),
            sa.Column("updated_at", sa.String(), nullable=False),
            sa.Column("version", sa.Integer(), nullable=False),
            sa.Column("data_json", sa.Text(), nullable=False),
            *[
                sa.Column(
                    field,
                    sa.String(),
                    sa.ForeignKey(f"{table}.id"),
                    nullable=nullable,
                    unique=field == unique,
                )
                for field, table, nullable in refs
            ],
            *(
                [sa.Column("operation_id", sa.String(36), unique=True, nullable=False)]
                if unique == "operation_id"
                else []
            ),
        )
        op.create_index(f"ix_{name}_owner_id", name, ["owner_id"])
        for field, _, _ in refs:
            if field in {"notebook_id", "page_id"} and unique != field:
                op.create_index(f"ix_{name}_{field}", name, [field])


def downgrade() -> None:
    raise RuntimeError(
        "Reversão destrutiva bloqueada. Restaure um backup validado após confirmação."
    )
