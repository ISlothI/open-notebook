"""Runs migrations online; an advisory lock serialises concurrent starts."""

from alembic import context
from sqlalchemy import text

from open_notebook.infrastructure.database import build_engine
from open_notebook.infrastructure.logging import configure_logging
from open_notebook.settings import Settings

MIGRATION_LOCK_ID = 7_406_001

settings = Settings()
configure_logging(settings, "migrate")

with build_engine(settings).connect() as connection:
    connection.execute(text("SELECT pg_advisory_lock(:id)"), {"id": MIGRATION_LOCK_ID})
    # A session-level lock survives this commit and is released when the connection closes.
    connection.commit()
    context.configure(connection=connection, target_metadata=None)
    with context.begin_transaction():
        context.run_migrations()
