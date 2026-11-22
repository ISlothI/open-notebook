"""HTTP interface of the embedding model; reachable only inside the cluster network."""

from typing import Annotated, Protocol

from fastapi import FastAPI
from prometheus_client import Histogram
from pydantic import BaseModel, Field, StringConstraints

from open_notebook.domain.search import Vector
from open_notebook.entrypoints.api.health import build_health_router
from open_notebook.entrypoints.api.observability import install_observability

MAX_TEXTS = 2_000
MAX_TEXT_LENGTH = 4_000

EMBEDDED_TEXTS = Histogram(
    "embedder_texts_per_request", "Texts per request", buckets=(1, 2, 5, 10, 50, 200)
)


class Embedder(Protocol):
    def embed(self, texts: list[str]) -> list[Vector]: ...


class EmbedRequest(BaseModel):
    texts: Annotated[
        list[Annotated[str, StringConstraints(max_length=MAX_TEXT_LENGTH)]],
        Field(min_length=1, max_length=MAX_TEXTS),
    ]


class EmbedResponse(BaseModel):
    vectors: list[Vector]


class AlwaysAvailable:
    """The model is loaded before the server starts to listen."""

    def is_available(self) -> bool:
        return True


def create_app(embedder: Embedder, version: str) -> FastAPI:
    app = FastAPI(title="Open Notebook embedder", version=version, docs_url=None, redoc_url=None)
    install_observability(app)
    app.include_router(build_health_router(AlwaysAvailable(), version))

    @app.post("/embed")
    def embed(body: EmbedRequest) -> EmbedResponse:
        EMBEDDED_TEXTS.observe(len(body.texts))
        return EmbedResponse(vectors=embedder.embed(body.texts))

    return app
