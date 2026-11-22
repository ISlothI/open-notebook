"""Pages and their immutable versions."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from open_notebook.domain.errors import DomainError, InvalidValueError

MAX_CONTENT_BYTES = 1_000_000
FIRST_VERSION = 1


@dataclass(frozen=True)
class PageVersion:
    page_id: UUID
    number: int
    title: str
    content: str
    created_at: datetime
    restored_from: int | None

    def has_text(self, title: str, content: str) -> bool:
        return self.title == title and self.content == content


@dataclass(frozen=True)
class VersionSummary:
    number: int
    title: str
    created_at: datetime
    restored_from: int | None


@dataclass(frozen=True)
class SaveResult:
    version: PageVersion
    created: bool


class VersionConflictError(DomainError):
    """Somebody saved the page since the caller read it."""

    code = "version_conflict"

    def __init__(self, current: PageVersion) -> None:
        super().__init__("The page has been changed since it was opened.")
        self.current = current


def clean_content(content: str) -> str:
    if "\x00" in content:
        raise InvalidValueError("The content must not contain NUL characters.")
    if len(content.encode()) > MAX_CONTENT_BYTES:
        raise InvalidValueError(f"The content must not exceed {MAX_CONTENT_BYTES} bytes.")
    return content.replace("\r\n", "\n")
