from fastapi.testclient import TestClient

from open_notebook.domain.search import Vector
from open_notebook.entrypoints.embedder.app import MAX_TEXT_LENGTH, create_app


class FakeModel:
    def embed(self, texts: list[str]) -> list[Vector]:
        return [[float(len(text))] for text in texts]


client = TestClient(create_app(FakeModel(), "1.2.3"))


def test_embed() -> None:
    response = client.post("/embed", json={"texts": ["a", "bb"]})

    assert response.json() == {"vectors": [[1.0], [2.0]]}


def test_invalid_requests_are_refused() -> None:
    bodies: list[dict[str, list[str]]] = [
        {},
        {"texts": []},
        {"texts": ["x" * (MAX_TEXT_LENGTH + 1)]},
    ]
    for body in bodies:
        assert client.post("/embed", json=body).status_code == 422


def test_health() -> None:
    assert client.get("/api/health/ready").status_code == 200
