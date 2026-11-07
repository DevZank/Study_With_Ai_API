from alembic import context
from study_api.infrastructure.db.database import database_path, engine_for
from study_api.infrastructure.db.models import Base

engine = engine_for(database_path())
with engine.connect() as connection:
    context.configure(
        connection=connection, target_metadata=Base.metadata, render_as_batch=True
    )
    with context.begin_transaction():
        context.run_migrations()
engine.dispose()
