"""Use cases of page content and versions."""

from uuid import UUID

import structlog

from open_notebook.application.access import require_active_page
from open_notebook.application.ports import Transaction, TransactionFactory
from open_notebook.domain.errors import NotFoundError
from open_notebook.domain.library import clean_title
from open_notebook.domain.pages import (
    PageVersion,
    SaveResult,
    VersionConflictError,
    VersionSummary,
    clean_content,
)

log = structlog.get_logger(__name__)


def save_version(
    tx: Transaction,
    current: PageVersion,
    title: str,
    content: str,
    restored_from: int | None = None,
) -> SaveResult:
    """Appends a version to a locked page; saving unchanged text is a no-op."""
    if current.has_text(title, content):
        return SaveResult(current, created=False)
    version = tx.pages.append(current.page_id, current.number + 1, title, content, restored_from)
    tx.nodes.rename(current.page_id, title)
    log.info("page_saved", page_id=str(version.page_id), number=version.number)
    return SaveResult(version, created=True)


class PageService:
    def __init__(self, transactions: TransactionFactory) -> None:
        self._transactions = transactions

    def read(self, owner_id: UUID, page_id: UUID) -> PageVersion:
        with self._transactions() as tx:
            require_active_page(tx, owner_id, page_id)
            return tx.pages.current(page_id)

    def save(
        self, owner_id: UUID, page_id: UUID, title: str, content: str, base_version: int
    ) -> SaveResult:
        cleaned_title, cleaned_content = clean_title(title), clean_content(content)
        with self._transactions() as tx:
            require_active_page(tx, owner_id, page_id)
            current = tx.pages.lock(page_id)
            # A retried request finds its own text already saved, which is not a conflict.
            is_retry = current.has_text(cleaned_title, cleaned_content)
            if base_version != current.number and not is_retry:
                raise VersionConflictError(current)
            return save_version(tx, current, cleaned_title, cleaned_content)

    def list_versions(self, owner_id: UUID, page_id: UUID) -> list[VersionSummary]:
        with self._transactions() as tx:
            require_active_page(tx, owner_id, page_id)
            return tx.pages.list_versions(page_id)

    def read_version(self, owner_id: UUID, page_id: UUID, number: int) -> PageVersion:
        with self._transactions() as tx:
            require_active_page(tx, owner_id, page_id)
            return self._require_version(tx, page_id, number)

    def restore_version(self, owner_id: UUID, page_id: UUID, number: int) -> SaveResult:
        """Nothing is lost: the old text becomes a new version."""
        with self._transactions() as tx:
            require_active_page(tx, owner_id, page_id)
            current = tx.pages.lock(page_id)
            old = self._require_version(tx, page_id, number)
            return save_version(tx, current, old.title, old.content, restored_from=number)

    @staticmethod
    def _require_version(tx: Transaction, page_id: UUID, number: int) -> PageVersion:
        version = tx.pages.version(page_id, number)
        if version is None:
            raise NotFoundError("The version does not exist.")
        return version
