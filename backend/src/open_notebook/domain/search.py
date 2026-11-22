"""Search queries, indexed text and results."""

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from open_notebook.domain.errors import InvalidValueError

MAX_QUERY_LENGTH = 300

type Vector = list[float]


@dataclass(frozen=True)
class Chunk:
    """A part of a page that is found on its own."""

    title: str
    text: str


class SearchMode(StrEnum):
    HYBRID = "hybrid"
    FULL_TEXT = "fulltext"


@dataclass(frozen=True)
class SnippetPart:
    text: str
    is_match: bool


@dataclass(frozen=True)
class SearchHit:
    page_id: UUID
    title: str
    section_title: str
    notebook_id: UUID
    notebook_title: str
    snippet: list[SnippetPart]


@dataclass(frozen=True)
class SearchResults:
    mode: SearchMode
    hits: list[SearchHit]


def clean_query(query: str) -> str:
    cleaned = " ".join(query.replace("\x00", " ").split())
    if not cleaned:
        raise InvalidValueError("The search must not be empty.")
    if len(cleaned) > MAX_QUERY_LENGTH:
        raise InvalidValueError(f"The search must not exceed {MAX_QUERY_LENGTH} characters.")
    return cleaned
