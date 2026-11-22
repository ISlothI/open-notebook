"""Keeps the search index in step with the pages."""

from uuid import UUID

import structlog

from open_notebook.application.jobs import INDEX_PAGE, Job, JobOutbox, TransientError
from open_notebook.application.ports import (
    Clock,
    EmbeddingProvider,
    EmbeddingUnavailableError,
    IndexingObserver,
    PageChunker,
    TransactionFactory,
)
from open_notebook.domain.pages import PageVersion
from open_notebook.domain.search import Chunk, Vector

log = structlog.get_logger(__name__)


def request_indexing(jobs: JobOutbox, page_id: UUID) -> None:
    """Saves in quick succession share one waiting job, which reads the latest version."""
    jobs.enqueue(INDEX_PAGE, {"page_id": str(page_id)}, dedupe_key=f"{INDEX_PAGE}:{page_id}")


def passage(chunk: Chunk) -> str:
    return f"{chunk.title}\n{chunk.text}"


class IndexPage:
    def __init__(
        self,
        transactions: TransactionFactory,
        chunker: PageChunker,
        embeddings: EmbeddingProvider,
        clock: Clock,
        observer: IndexingObserver,
    ) -> None:
        self._transactions = transactions
        self._chunker = chunker
        self._embeddings = embeddings
        self._clock = clock
        self._observer = observer

    def __call__(self, job: Job) -> None:
        page_id = UUID(job.payload["page_id"])
        with self._transactions() as tx:
            version = tx.pages.find_current(page_id)
        if version is None:
            log.info("page_is_gone", page_id=str(page_id))
            return

        chunks = self._chunker.chunk(version.title, version.content)
        try:
            vectors = self._embeddings.embed_passages([passage(chunk) for chunk in chunks])
        except EmbeddingUnavailableError as error:
            # Full-text search works without vectors, so the page is findable meanwhile.
            self._store(version, chunks, None)
            raise TransientError("embedder unavailable") from error
        if self._store(version, chunks, vectors):
            lag = self._clock() - version.created_at
            self._observer.indexed(lag.total_seconds())

    def _store(
        self, version: PageVersion, chunks: list[Chunk], vectors: list[Vector] | None
    ) -> bool:
        with self._transactions() as tx:
            current = tx.pages.lock_if_exists(version.page_id)
            if current is None or current.number != version.number:
                # A newer version has its own job.
                return False
            tx.search.replace_chunks(version.page_id, chunks, vectors)
            return True
