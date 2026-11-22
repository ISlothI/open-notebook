"""Connects the use cases with their adapters."""

from datetime import UTC, datetime

from sqlalchemy import Engine

from open_notebook.application.accounts import AccountService
from open_notebook.application.library import LibraryService
from open_notebook.application.pages import PageService
from open_notebook.application.services import Services
from open_notebook.infrastructure.passwords import Argon2PasswordHasher
from open_notebook.infrastructure.postgres.transaction import PostgresTransactions


def utc_now() -> datetime:
    return datetime.now(UTC)


def build_services(engine: Engine) -> Services:
    transactions = PostgresTransactions(engine)
    return Services(
        accounts=AccountService(transactions, Argon2PasswordHasher(), utc_now),
        library=LibraryService(transactions),
        pages=PageService(transactions),
    )
