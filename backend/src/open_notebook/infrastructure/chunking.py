"""Splits Markdown into plain-text chunks along its headings."""

from markdown_it import MarkdownIt
from markdown_it.token import Token

from open_notebook.domain.search import Chunk

# Fits into the token limit of the embedding model for typical Hungarian and English text.
MAX_CHUNK_LENGTH = 450
HEADING_SEPARATOR = " / "


def plain_text(inline: Token) -> str:
    parts = []
    for child in inline.children or []:
        if child.type in {"softbreak", "hardbreak"}:
            parts.append("\n")
        elif child.type != "html_inline":
            parts.append(child.content)
    return "".join(parts)


def split_long(block: str) -> list[str]:
    """Splits at word boundaries; text without spaces is cut."""
    pieces = []
    while len(block) > MAX_CHUNK_LENGTH:
        cut = block.rfind(" ", 1, MAX_CHUNK_LENGTH)
        cut = cut if cut > 0 else MAX_CHUNK_LENGTH
        pieces.append(block[:cut].strip())
        block = block[cut:].strip()
    return [*pieces, block]


class MarkdownChunker:
    def __init__(self) -> None:
        self._parser = MarkdownIt("commonmark").enable(["table", "strikethrough"])

    def chunk(self, title: str, content: str) -> list[Chunk]:
        chunks = [
            chunk
            for heading, blocks in self._sections(content)
            for chunk in self._pack(title, heading, blocks)
        ]
        return chunks or [Chunk(title, "")]

    def _sections(self, content: str) -> list[tuple[str, list[str]]]:
        sections: list[tuple[str, list[str]]] = [("", [])]
        in_heading = False
        for token in self._parser.parse(content):
            if token.type == "heading_open":
                in_heading = True
            elif token.type == "inline" and in_heading:
                sections.append((plain_text(token), []))
                in_heading = False
            elif token.type == "inline":
                sections[-1][1].append(plain_text(token))
            elif token.type in {"fence", "code_block"}:
                sections[-1][1].append(token.content)
        return sections

    @staticmethod
    def _pack(title: str, heading: str, blocks: list[str]) -> list[Chunk]:
        texts = [""]
        for block in blocks:
            for piece in split_long(block.strip()):
                if texts[-1] and len(texts[-1]) + len(piece) > MAX_CHUNK_LENGTH:
                    texts.append(piece)
                else:
                    texts[-1] = f"{texts[-1]}\n{piece}".strip()
        # A heading without text is still worth finding.
        chunk_title = f"{title}{HEADING_SEPARATOR}{heading}" if heading else title
        return [Chunk(chunk_title, text) for text in texts if text or heading]
