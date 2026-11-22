"""Connects the use cases with their adapters."""

from datetime import UTC, datetime

from sqlalchemy import Engine

from open_notebook.application.accounts import AccountService
from open_notebook.application.indexing import IndexPage
from open_notebook.application.jobs import INDEX_PAGE, JobHandler
from open_notebook.application.library import LibraryService
from open_notebook.application.pages import PageService
from open_notebook.application.ports import EmbeddingProvider
from open_notebook.application.search import SearchService
from open_notebook.application.services import Services
from open_notebook.infrastructure.chunking import MarkdownChunker
from open_notebook.infrastructure.job_metrics import IndexingMetrics
from open_notebook.infrastructure.passwords import Argon2PasswordHasher
from open_notebook.infrastructure.postgres.transaction import PostgresTransactions


def utc_now() -> datetime:
    return datetime.now(UTC)


def build_services(engine: Engine, embeddings: EmbeddingProvider) -> Services:
    transactions = PostgresTransactions(engine)
    return Services(
        accounts=AccountService(transactions, Argon2PasswordHasher(), utc_now),
        library=LibraryService(transactions),
        pages=PageService(transactions),
        search=SearchService(transactions, embeddings),
    )


def build_handlers(engine: Engine, embeddings: EmbeddingProvider) -> dict[str, JobHandler]:
    transactions = PostgresTransactions(engine)
    return {
        INDEX_PAGE: IndexPage(
            transactions, MarkdownChunker(), embeddings, utc_now, IndexingMetrics()
        ),
    }
