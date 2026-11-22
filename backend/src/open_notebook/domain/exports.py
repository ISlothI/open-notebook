"""PDF exports of a page or a notebook."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class ExportState(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    EXPIRED = "expired"


UNFINISHED = frozenset({ExportState.QUEUED, ExportState.RUNNING})


@dataclass(frozen=True)
class Export:
    id: UUID
    item_id: UUID
    title: str
    state: ExportState
    progress: int
    created_at: datetime
    finished_at: datetime | None
    expires_at: datetime | None


@dataclass(frozen=True)
class PageReference:
    """An immutable version, so the export shows what existed when it was requested."""

    page_id: UUID
    number: int


@dataclass(frozen=True)
class SnapshotSection:
    title: str
    pages: list[PageReference]


@dataclass(frozen=True)
class Snapshot:
    title: str
    created_at: datetime
    sections: list[SnapshotSection]
    # A single page has no cover and no section headings.
    is_notebook: bool


@dataclass(frozen=True)
class DocumentPage:
    title: str
    content: str


@dataclass(frozen=True)
class DocumentSection:
    title: str
    pages: list[DocumentPage]


@dataclass(frozen=True)
class Document:
    title: str
    created_at: datetime
    sections: list[DocumentSection]
    is_notebook: bool
