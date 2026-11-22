"""Speaks the language of the product, so that tests read like user flows."""

from typing import Any

from fastapi.testclient import TestClient

PASSWORD = "correct horse battery"  # noqa: S105 - fictional account of the tests

type Json = dict[str, Any]


class NotebookClient:
    def __init__(self, http: TestClient) -> None:
        self.http = http

    def register(self, email: str) -> Json:
        response = self.http.post("/api/auth/register", json={"email": email, "password": PASSWORD})
        assert response.status_code == 201, response.text
        body: Json = response.json()
        return body

    def create(self, kind: str, title: str, parent: Json | None = None) -> Json:
        response = self.http.post(
            "/api/items",
            json={"kind": kind, "title": title, "parent_id": parent["id"] if parent else None},
        )
        assert response.status_code == 201, response.text
        body: Json = response.json()
        return body

    def create_page(self, title: str = "Page") -> Json:
        notebook = self.create("notebook", "Notebook")
        return self.create("page", title, self.create("section", "Section", notebook))

    def save(self, page: Json, title: str, content: str, base: int) -> Json:
        response = self.try_save(page, title, content, base)
        assert response.status_code == 200, response.text
        body: Json = response.json()
        return body

    def try_save(self, page: Json, title: str, content: str, base: int) -> Any:  # noqa: ANN401
        return self.http.put(
            f"/api/pages/{page['id']}",
            json={"title": title, "content": content, "base_version": base},
        )

    def read(self, page: Json) -> Json:
        response = self.http.get(f"/api/pages/{page['id']}")
        assert response.status_code == 200, response.text
        body: Json = response.json()
        return body

    def versions(self, page: Json) -> list[Json]:
        body: list[Json] = self.http.get(f"/api/pages/{page['id']}/versions").json()
        return body

    def titles(self) -> list[str]:
        return [item["title"] for item in self.http.get("/api/items").json()]

    def trash(self, item: Json) -> None:
        response = self.http.delete(f"/api/items/{item['id']}")
        assert response.status_code == 204, response.text

    def trashed_titles(self) -> list[str]:
        return [item["title"] for item in self.http.get("/api/trash").json()]

    def restore(self, item: Json, parent: Json | None = None) -> Any:  # noqa: ANN401
        return self.http.post(
            f"/api/trash/{item['id']}/restore", json={"parent_id": parent["id"] if parent else None}
        )

    def move(self, item: Json, parent: Json | None, position: int = 0) -> Any:  # noqa: ANN401
        return self.http.post(
            f"/api/items/{item['id']}/move",
            json={"parent_id": parent["id"] if parent else None, "position": position},
        )

    def search(self, query: str, notebook: Json | None = None) -> Json:
        params = {"q": query} | ({"notebook_id": notebook["id"]} if notebook else {})
        response = self.http.get("/api/search", params=params)
        assert response.status_code == 200, response.text
        body: Json = response.json()
        return body

    def found_titles(self, query: str, notebook: Json | None = None) -> list[str]:
        return [hit["title"] for hit in self.search(query, notebook)["hits"]]
