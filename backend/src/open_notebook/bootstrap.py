"""Connects the use cases with their adapters."""

from datetime import UTC, datetime

from sqlalchemy import Engine

from open_notebook.application.accounts import AccountService
from open_notebook.application.cleanup import Cleanup
from open_notebook.application.exports import ExportPdf, ExportService
from open_notebook.application.indexing import IndexPage
from open_notebook.application.jobs import (
    EXPORT_PDF,
    INDEX_PAGE,
    JobHandler,
    JobObserver,
    JobProcessor,
    JobStore,
)
from open_notebook.application.library import LibraryService
from open_notebook.application.pages import PageService
from open_notebook.application.ports import EmbeddingProvider
from open_notebook.application.search import SearchService
from open_notebook.application.services import Services
from open_notebook.infrastructure.chunking import MarkdownChunker
from open_notebook.infrastructure.job_metrics import ExportMetrics, IndexingMetrics
from open_notebook.infrastructure.passwords import Argon2PasswordHasher
from open_notebook.infrastructure.pdf import WeasyPrintRenderer
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
        exports=ExportService(transactions, utc_now),
    )


def build_job_processor(
    engine: Engine, store: JobStore, embeddings: EmbeddingProvider, observer: JobObserver
) -> JobProcessor:
    transactions = PostgresTransactions(engine)
    export_pdf = ExportPdf(transactions, WeasyPrintRenderer(), utc_now, ExportMetrics())
    handlers: dict[str, JobHandler] = {
        INDEX_PAGE: IndexPage(
            transactions, MarkdownChunker(), embeddings, utc_now, IndexingMetrics()
        ),
        EXPORT_PDF: export_pdf,
    }
    return JobProcessor(store, handlers, observer, on_dead={EXPORT_PDF: export_pdf.give_up})


def build_cleanup(engine: Engine) -> Cleanup:
    return Cleanup(PostgresTransactions(engine), utc_now)
