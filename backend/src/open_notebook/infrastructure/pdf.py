"""Renders documents to PDF."""

import html
from collections.abc import Iterator
from dataclasses import dataclass
from typing import NoReturn

import weasyprint
from markdown_it import MarkdownIt
from markdown_it.token import Token

from open_notebook.domain.exports import Document, DocumentPage

LOWEST_HEADING = 6
TOC_HEADING_DEPTH = 3
CHECKBOXES = {"[ ] ": "☐ ", "[x] ": "☑ ", "[X] ": "☑ "}

BOOKMARK = '<svg viewBox="0 0 9 22"><path fill="#c0361d" d="M0 0h9v22l-4.5-4.5L0 22z"/></svg>'

STYLE = """
@page {
  size: A4;
  margin: 26mm 24mm 24mm;
  @top-left { content: string(document); }
  @top-right { content: string(page); }
  @bottom-center { content: counter(page); }
  @top-left, @top-right, @bottom-center {
    color: #5a6275; font-family: Newsreader, serif; font-size: 9pt;
  }
}
@page cover { @top-left { content: none } @top-right { content: none }
              @bottom-center { content: none } }
html { color: #1b2436; font: 11pt/1.55 Newsreader, "DejaVu Serif", serif; hyphens: auto; }
h1, h2, h3, h4, h5, h6 { font-weight: 500; line-height: 1.25; break-after: avoid; hyphens: none; }
.document-title { string-set: document content(); }
.cover { page: cover; break-after: page; padding-top: 78mm; }
.cover svg { width: 9mm; height: 22mm; margin-bottom: 14mm; }
.cover h1 { font-size: 38pt; margin: 0 0 6mm; }
.cover p { color: #5a6275; }
.toc { break-after: page; }
.single .toc { break-after: auto; margin-bottom: 10mm; }
.toc h2 { font-size: 16pt; }
.toc ul { list-style: none; margin: 0; padding: 0; }
.toc li { margin: 1.5mm 0; }
.toc .level-2 { padding-left: 6mm; }
.toc .level-3 { padding-left: 12mm; }
.toc a { color: inherit; text-decoration: none; }
.toc a::after { content: leader(dotted) " " target-counter(attr(href), page); }
.section-title { font-size: 24pt; break-before: page; bookmark-level: 1; }
.page { break-before: page; }
.section-title + .page, .single .page { break-before: auto; }
.page-title { font-size: 22pt; margin: 0 0 6mm; string-set: page content(); }
.page h2 { font-size: 17pt } .page h3 { font-size: 15pt } .page h4 { font-size: 13.5pt }
.page h5 { font-size: 12pt } .page h6 { font-size: 11pt }
pre, code { font-family: "DejaVu Sans Mono", monospace; font-size: 8.5pt; hyphens: none; }
pre { background: #f8f4ec; padding: 4mm; border-radius: 2mm; white-space: pre-wrap; }
blockquote { margin: 4mm 0; padding-left: 5mm; border-left: 1mm solid #c0361d; color: #5a6275; }
table { border-collapse: collapse; width: 100%; margin: 4mm 0; }
th, td { border: .3mm solid #d9d4ca; padding: 1.5mm 2.5mm; text-align: left; }
a { color: #a32c16; overflow-wrap: anywhere; }
"""


@dataclass(frozen=True)
class TocEntry:
    level: int
    title: str
    anchor: str


class ExternalResourceError(Exception):
    """Documents must not make the server request anything (SSRF)."""


class NoResources(weasyprint.URLFetcher):  # type: ignore[misc]
    def fetch(self, url: str, headers: dict[str, str] | None = None) -> NoReturn:
        raise ExternalResourceError(url)


def anchors() -> Iterator[str]:
    number = 0
    while True:
        number += 1
        yield f"a{number}"


class WeasyPrintRenderer:
    def __init__(self) -> None:
        # Raw HTML stays text, so a note cannot bring its own markup or styles.
        self._markdown = MarkdownIt("commonmark", {"html": False}).enable(
            ["table", "strikethrough"]
        )

    def render(self, document: Document) -> bytes:
        source = weasyprint.HTML(string=self._to_html(document), url_fetcher=NoResources())
        pdf: bytes = source.write_pdf()
        return pdf

    def _to_html(self, document: Document) -> str:
        toc: list[TocEntry] = []
        anchor = anchors()
        body = []
        for section in document.sections:
            if document.is_notebook:
                entry = TocEntry(1, section.title, next(anchor))
                toc.append(entry)
                body.append(
                    f'<h1 class="section-title" id="{entry.anchor}">'
                    f"{html.escape(section.title)}</h1>"
                )
            body += [self._page(page, document.is_notebook, toc, anchor) for page in section.pages]
        style_class = "notebook" if document.is_notebook else "single"
        front = self._cover(document) if document.is_notebook else ""
        return (
            f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
            f"<title>{html.escape(document.title)}</title><style>{STYLE}</style></head>"
            f'<body class="{style_class}">{front}'
            f"{self._toc(toc)}{''.join(body)}</body></html>"
        )

    @staticmethod
    def _cover(document: Document) -> str:
        date = f"{document.created_at:%-d %B %Y}"
        return (
            f'<section class="cover">{BOOKMARK}'
            f'<h1 class="document-title" style="bookmark-level: none">'
            f"{html.escape(document.title)}</h1><p>{date}</p></section>"
        )

    @staticmethod
    def _toc(entries: list[TocEntry]) -> str:
        items = "".join(
            f'<li class="level-{entry.level}">'
            f'<a href="#{entry.anchor}">{html.escape(entry.title)}</a></li>'
            for entry in entries
        )
        return (
            f'<nav class="toc"><h2 style="bookmark-level: none">Contents</h2><ul>{items}</ul></nav>'
        )

    def _page(
        self, page: DocumentPage, in_notebook: bool, toc: list[TocEntry], anchor: Iterator[str]
    ) -> str:
        title_level = 2 if in_notebook else 1
        entry = TocEntry(title_level, page.title, next(anchor))
        toc.append(entry)
        tokens = self._markdown.parse(page.content)
        show_checkboxes(tokens)
        headings = list(shift_headings(tokens, title_level, anchor))
        if not in_notebook:
            toc += [heading for heading in headings if heading.level <= TOC_HEADING_DEPTH]
        content = self._markdown.renderer.render(tokens, self._markdown.options, {})
        return (
            f'<article class="page"><h1 class="page-title" id="{entry.anchor}" '
            f'style="bookmark-level: {title_level}">{html.escape(page.title)}</h1>'
            f"{content}</article>"
        )


def shift_headings(tokens: list[Token], below: int, anchor: Iterator[str]) -> Iterator[TocEntry]:
    """Puts the headings of a page under its title and makes them link targets."""
    for position, token in enumerate(tokens):
        if token.type not in {"heading_open", "heading_close"}:
            continue
        level = min(int(token.tag[1]) + below, LOWEST_HEADING)
        token.tag = f"h{level}"
        if token.type == "heading_open":
            entry = TocEntry(level, tokens[position + 1].content, next(anchor))
            token.attrSet("id", entry.anchor)
            yield entry


def show_checkboxes(tokens: list[Token]) -> None:
    """Task lists become ballot boxes, because form fields make no sense on paper."""
    for opening, paragraph, inline in zip(tokens, tokens[1:], tokens[2:], strict=False):
        if opening.type != "list_item_open" or paragraph.type != "paragraph_open":
            continue
        first = inline.children[0] if inline.children else None
        if first is None or first.type != "text":
            continue
        for marker, symbol in CHECKBOXES.items():
            if first.content.startswith(marker):
                first.content = symbol + first.content[len(marker) :]
