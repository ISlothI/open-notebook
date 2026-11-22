"""Search across the notes of one user."""

from uuid import UUID

import structlog

from open_notebook.application.ports import (
    EmbeddingProvider,
    EmbeddingUnavailableError,
    TransactionFactory,
)
from open_notebook.domain.search import SearchMode, SearchResults, Vector, clean_query

RESULT_LIMIT = 20

log = structlog.get_logger(__name__)


class SearchService:
    def __init__(self, transactions: TransactionFactory, embeddings: EmbeddingProvider) -> None:
        self._transactions = transactions
        self._embeddings = embeddings

    def search(self, owner_id: UUID, query: str, notebook_id: UUID | None) -> SearchResults:
        """Falls back to full-text search when the query cannot be embedded."""
        cleaned = clean_query(query)
        vector = self._embed(cleaned)
        with self._transactions() as tx:
            hits = tx.search.find(owner_id, cleaned, vector, notebook_id, RESULT_LIMIT)
        return SearchResults(SearchMode.HYBRID if vector else SearchMode.FULL_TEXT, hits)

    def _embed(self, query: str) -> Vector | None:
        try:
            return self._embeddings.embed_query(query)
        except EmbeddingUnavailableError as error:
            log.warning("search_degraded", reason=str(error))
            return None
