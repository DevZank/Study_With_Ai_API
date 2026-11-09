from alembic import context
from study_api.infrastructure.db.database import database_path, engine_for
from study_api.infrastructure.db.notebooks import NotebookRow
from study_api.infrastructure.db.trails import TrailRow

engine = engine_for(database_path())
assert NotebookRow.metadata is TrailRow.metadata
with engine.connect() as connection:
    context.configure(
        connection=connection, target_metadata=TrailRow.metadata, render_as_batch=True
    )
    with context.begin_transaction():
        context.run_migrations()
engine.dispose()
