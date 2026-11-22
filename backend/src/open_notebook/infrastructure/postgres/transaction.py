"""Database transactions that give access to the repositories."""

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass

from sqlalchemy import Connection, Engine

from open_notebook.infrastructure.postgres.accounts import PostgresAccounts
from open_notebook.infrastructure.postgres.jobs import PostgresJobOutbox
from open_notebook.infrastructure.postgres.nodes import PostgresNodes
from open_notebook.infrastructure.postgres.pages import PostgresPages
from open_notebook.infrastructure.postgres.search import PostgresSearchIndex


@dataclass(frozen=True)
class PostgresTransaction:
    nodes: PostgresNodes
    pages: PostgresPages
    accounts: PostgresAccounts
    search: PostgresSearchIndex
    jobs: PostgresJobOutbox


def open_transaction(connection: Connection) -> PostgresTransaction:
    return PostgresTransaction(
        nodes=PostgresNodes(connection),
        pages=PostgresPages(connection),
        accounts=PostgresAccounts(connection),
        search=PostgresSearchIndex(connection),
        jobs=PostgresJobOutbox(connection),
    )


class PostgresTransactions:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    @contextmanager
    def __call__(self) -> Iterator[PostgresTransaction]:
        with self._engine.begin() as connection:
            yield open_transaction(connection)
