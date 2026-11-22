import io
import threading
from collections.abc import Iterator
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
from pypdf import PdfReader

from open_notebook.domain.exports import Document, DocumentPage, DocumentSection
from open_notebook.infrastructure.pdf import WeasyPrintRenderer

CREATED = datetime(2026, 11, 22, tzinfo=UTC)


def render(document: Document) -> PdfReader:
    return PdfReader(io.BytesIO(WeasyPrintRenderer().render(document)))


def notebook(*sections: DocumentSection) -> Document:
    return Document("My notebook", CREATED, list(sections), is_notebook=True)


def single(content: str, title: str = "My page") -> Document:
    page = DocumentPage(title, content)
    return Document(title, CREATED, [DocumentSection("", [page])], is_notebook=False)


def text_of(reader: PdfReader) -> str:
    return "\n".join(page.extract_text() for page in reader.pages)


def outline_titles(reader: PdfReader) -> list[object]:
    def titles(items: list[object]) -> list[object]:
        return [
            titles(item) if isinstance(item, list) else getattr(item, "title", None)
            for item in items
        ]

    return titles(list(reader.outline))


def test_notebook_has_cover_contents_pages_and_bookmarks() -> None:
    reader = render(
        notebook(
            DocumentSection("First", [DocumentPage("A", "alpha"), DocumentPage("B", "beta")]),
            DocumentSection("Second", [DocumentPage("C", "gamma")]),
        )
    )

    pages = [page.extract_text() for page in reader.pages]
    assert "My notebook" in pages[0]
    assert "22 November 2026" in pages[0]
    assert "Contents" in pages[1]
    assert outline_titles(reader) == ["First", ["A", "B"], "Second", ["C"]]
    for title, text in (("A", "alpha"), ("B", "beta"), ("C", "gamma")):
        number = next(i for i, page in enumerate(pages, 1) if text in page)
        line = next(row for row in pages[1].splitlines() if row.startswith(f"{title} "))
        assert line.endswith(str(number)), f"{title} should be listed on page {number}: {line}"


def test_single_page_lists_its_headings() -> None:
    reader = render(single("# One\n\ntext\n\n## Two\n\ntext\n"))

    first = reader.pages[0].extract_text()
    assert "Contents" in first
    assert outline_titles(reader) == ["My page", ["One", ["Two"]]]


def test_hungarian_text_and_task_lists_are_readable() -> None:
    text = text_of(render(single("Árvíztűrő tükörfúrógép\n\n- [ ] nyitott\n- [x] kész\n")))

    assert "Árvíztűrő tükörfúrógép" in text
    assert "☐ nyitott" in text
    assert "☑ kész" in text


def test_raw_html_stays_text() -> None:
    text = text_of(render(single("<script>x</script>\n\n<b>bold</b>", title="<i>title</i>")))

    assert "<script>" in text
    assert "<b>bold</b>" in text
    assert "<i>title</i>" in text


@pytest.fixture
def requests_seen() -> Iterator[tuple[str, list[str]]]:
    seen: list[str] = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            seen.append(self.path)
            self.send_response(404)
            self.end_headers()

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}", seen
    server.shutdown()
    thread.join()
    server.server_close()


def test_rendering_never_requests_anything(requests_seen: tuple[str, list[str]]) -> None:
    url, seen = requests_seen
    attacks = [
        f"![image]({url}/image.png)",
        f'<img src="{url}/html.png">',
        f'<link rel="stylesheet" href="{url}/style.css">',
        f"<style>@import url({url}/import.css);</style>",
        f"[link]({url}/link)",
        "![local](file:///etc/passwd)",
    ]

    reader = render(single("\n\n".join(attacks)))

    assert seen == []
    assert "root:" not in text_of(reader)
