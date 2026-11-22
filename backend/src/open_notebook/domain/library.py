"""The hierarchy of folders, notebooks, sections and pages."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from open_notebook.domain.errors import InvalidHierarchyError, InvalidValueError

MAX_TITLE_LENGTH = 200


class NodeKind(StrEnum):
    FOLDER = "folder"
    NOTEBOOK = "notebook"
    SECTION = "section"
    PAGE = "page"


# None stands for the root of the library.
ALLOWED_PARENTS: dict[NodeKind, frozenset[NodeKind | None]] = {
    NodeKind.FOLDER: frozenset({None, NodeKind.FOLDER}),
    NodeKind.NOTEBOOK: frozenset({None, NodeKind.FOLDER}),
    NodeKind.SECTION: frozenset({NodeKind.NOTEBOOK}),
    NodeKind.PAGE: frozenset({NodeKind.SECTION}),
}


@dataclass(frozen=True)
class Node:
    id: UUID
    kind: NodeKind
    parent_id: UUID | None
    title: str
    position: int
    created_at: datetime
    trashed_at: datetime | None

    @property
    def is_trashed(self) -> bool:
        return self.trashed_at is not None


def ensure_placement(kind: NodeKind, parent_kind: NodeKind | None) -> None:
    if parent_kind not in ALLOWED_PARENTS[kind]:
        place = f"a {parent_kind}" if parent_kind else "the root of the library"
        raise InvalidHierarchyError(f"A {kind} cannot be placed in {place}.")


def clean_title(title: str) -> str:
    cleaned = " ".join(title.split())
    if not cleaned:
        raise InvalidValueError("The title must not be empty.")
    if len(cleaned) > MAX_TITLE_LENGTH:
        raise InvalidValueError(f"The title must not exceed {MAX_TITLE_LENGTH} characters.")
    return cleaned
