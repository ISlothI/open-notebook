"""Runs migrations online; an advisory lock serialises concurrent starts."""

from alembic import context
from sqlalchemy import text

from open_notebook.infrastructure.database import build_engine
from open_notebook.infrastructure.logging import configure_logging
from open_notebook.settings import Settings

MIGRATION_LOCK_ID = 7_406_001

settings = Settings()
configure_logging(settings, "migrate")
engine = build_engine(settings)

with engine.connect() as connection:
    context.configure(connection=connection, target_metadata=None)
    with context.begin_transaction():
        # Transaction-scoped: a session lock would stay on the pooled connection.
        connection.execute(text("SELECT pg_advisory_xact_lock(:id)"), {"id": MIGRATION_LOCK_ID})
        context.run_migrations()

engine.dispose()
