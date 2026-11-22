"""Rebuilds the search index, for example after changing the model."""

from sqlalchemy import select

from open_notebook.application.indexing import request_indexing
from open_notebook.infrastructure.database import build_engine
from open_notebook.infrastructure.logging import configure_logging
from open_notebook.infrastructure.postgres.jobs import PostgresJobOutbox
from open_notebook.infrastructure.postgres.tables import pages
from open_notebook.settings import Settings


def main() -> None:
    settings = Settings()
    configure_logging(settings, "reindex")
    with build_engine(settings).begin() as connection:
        outbox = PostgresJobOutbox(connection)
        for page_id in connection.scalars(select(pages.c.node_id)).all():
            request_indexing(outbox, page_id)
