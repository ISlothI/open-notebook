from typing import Any

import httpx2
import pytest

from open_notebook.application.ports import EmbeddingUnavailableError
from open_notebook.domain.errors import InvalidValueError
from open_notebook.domain.search import clean_query
from open_notebook.infrastructure.chunking import MAX_CHUNK_LENGTH, MarkdownChunker
from open_notebook.infrastructure.embedding_client import (
    PAUSE_AFTER_FAILURE_SECONDS,
    HttpEmbeddings,
)
from open_notebook.infrastructure.postgres.search import to_snippet


def chunk(content: str, title: str = "Title") -> list[tuple[str, str]]:
    return [(item.title, item.text) for item in MarkdownChunker().chunk(title, content)]


def test_page_is_split_along_its_headings() -> None:
    assert chunk("intro\n\n# One\n\ntext *one*\n\n## Two\n\n- `a`\n- b\n") == [
        ("Title", "intro"),
        ("Title / One", "text one"),
        ("Title / Two", "a\nb"),
    ]


def test_empty_page_is_found_by_its_title() -> None:
    assert chunk("") == [("Title", "")]


def test_code_and_tables_are_indexed_but_markup_is_not() -> None:
    text = chunk(
        "| a | b |\n| - | - |\n| 1 | 2 |\n\n```py\nrun()\n```\n\n<b>x</b> [y](http://z)\n"
    )[0][1]

    assert text == "a\nb\n1\n2\nrun()\nx y"


def test_long_text_is_split_without_loss() -> None:
    words = [f"word{number}" for number in range(1_000)]
    chunks = chunk(" ".join(words) + "\n\n" + "x" * 3_000)

    assert all(len(text) <= MAX_CHUNK_LENGTH for _, text in chunks)
    joined = " ".join(text for _, text in chunks).split()
    assert joined[:1_000] == words
    assert "".join(joined[1_000:]) == "x" * 3_000


def test_query_is_cleaned() -> None:
    assert clean_query("  two \n words ") == "two words"
    for invalid in ("", "  ", "x" * 301):
        with pytest.raises(InvalidValueError):
            clean_query(invalid)


def test_snippet_marks_matches() -> None:
    row: Any = {"headline": "a \x02b\x03 c \x02d\x03", "beginning": "unused"}

    assert [(part.text, part.is_match) for part in to_snippet(row)] == [
        ("a ", False),
        ("b", True),
        (" c ", False),
        ("d", True),
    ]


def test_snippet_without_match_is_the_beginning() -> None:
    row: Any = {"headline": "whatever", "beginning": "start"}

    assert [(part.text, part.is_match) for part in to_snippet(row)] == [("start", False)]


class FakeServer:
    def __init__(self) -> None:
        self.status = 200
        self.requests = 0
        self.now = 0.0

    def client(self) -> HttpEmbeddings:
        http = httpx2.Client(
            base_url="http://embedder", transport=httpx2.MockTransport(self.handle)
        )
        return HttpEmbeddings(http, monotonic=lambda: self.now)

    def handle(self, _request: httpx2.Request) -> httpx2.Response:
        self.requests += 1
        return httpx2.Response(self.status, json={"vectors": [[1.0, 0.0]]})


def test_client_returns_vectors() -> None:
    assert FakeServer().client().embed_query("q") == [1.0, 0.0]


def test_client_pauses_after_a_failure_and_recovers() -> None:
    server = FakeServer()
    client = server.client()
    server.status = 503
    for _ in range(3):
        with pytest.raises(EmbeddingUnavailableError):
            client.embed_query("q")
    assert server.requests == 1

    server.status = 200
    server.now = PAUSE_AFTER_FAILURE_SECONDS
    assert client.embed_query("q") == [1.0, 0.0]


@pytest.mark.parametrize("body", [b"not json", b"{}"])
def test_client_treats_a_malformed_answer_as_outage(body: bytes) -> None:
    http = httpx2.Client(
        base_url="http://embedder",
        transport=httpx2.MockTransport(lambda _request: httpx2.Response(200, content=body)),
    )
    with pytest.raises(EmbeddingUnavailableError):
        HttpEmbeddings(http).embed_passages(["p"])
