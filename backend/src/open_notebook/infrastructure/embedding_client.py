"""HTTP client of the embedder."""

import time
from collections.abc import Callable

import httpx2

from open_notebook.application.ports import EmbeddingUnavailableError
from open_notebook.domain.search import Vector

QUERY_TIMEOUT_SECONDS = 1.0
PASSAGE_TIMEOUT_SECONDS = 60.0
# While the embedder is down, searches must not wait for it one by one.
PAUSE_AFTER_FAILURE_SECONDS = 5.0


class HttpEmbeddings:
    def __init__(
        self, http: httpx2.Client, monotonic: Callable[[], float] = time.monotonic
    ) -> None:
        self._http = http
        self._monotonic = monotonic
        self._paused_until = 0.0

    def embed_query(self, query: str) -> Vector:
        if self._monotonic() < self._paused_until:
            raise EmbeddingUnavailableError("paused after a failure")
        try:
            return self._embed([query], QUERY_TIMEOUT_SECONDS)[0]
        except EmbeddingUnavailableError:
            self._paused_until = self._monotonic() + PAUSE_AFTER_FAILURE_SECONDS
            raise

    def embed_passages(self, passages: list[str]) -> list[Vector]:
        return self._embed(passages, PASSAGE_TIMEOUT_SECONDS)

    def _embed(self, texts: list[str], timeout: float) -> list[Vector]:
        try:
            response = self._http.post("/embed", json={"texts": texts}, timeout=timeout)
            response.raise_for_status()
            vectors: list[Vector] = response.json()["vectors"]
        except (httpx2.HTTPError, ValueError, KeyError) as error:
            raise EmbeddingUnavailableError(type(error).__name__) from error
        return vectors


def build_embeddings(url: str) -> HttpEmbeddings:
    return HttpEmbeddings(httpx2.Client(base_url=url))
