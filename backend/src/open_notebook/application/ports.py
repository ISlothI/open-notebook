"""What the use cases need from the outside world."""

from contextlib import AbstractContextManager
from datetime import datetime
from typing import Protocol
from uuid import UUID

from open_notebook.application.jobs import JobOutbox
from open_notebook.domain.accounts import User
from open_notebook.domain.library import Node, NodeKind
from open_notebook.domain.pages import PageVersion, VersionSummary
from open_notebook.domain.search import Chunk, SearchHit, Vector


class NodeRepository(Protocol):
    def lock_tree(self, owner_id: UUID) -> None:
        """Serialises structural changes of one owner until the transaction ends."""

    def list_active(self, owner_id: UUID) -> list[Node]: ...

    def list_trash(self, owner_id: UUID) -> list[Node]:
        """Only the items that were trashed themselves, not their descendants."""

    def get(self, owner_id: UUID, node_id: UUID) -> Node | None: ...

    def add(self, owner_id: UUID, kind: NodeKind, parent: Node | None, title: str) -> Node: ...

    def rename(self, node_id: UUID, title: str) -> None: ...

    def place(self, node: Node, parent: Node | None, position: int, owner_id: UUID) -> None: ...

    def is_inside(self, node_id: UUID, ancestor_id: UUID) -> bool: ...

    def is_trash_root(self, node_id: UUID) -> bool: ...

    def trash(self, node_id: UUID) -> None: ...

    def restore(self, node_id: UUID) -> None: ...


class PageRepository(Protocol):
    def create(self, page_id: UUID, title: str) -> None: ...

    def current(self, page_id: UUID) -> PageVersion: ...

    def lock(self, page_id: UUID) -> PageVersion:
        """The current version; concurrent saves wait until the transaction ends."""

    def find_current(self, page_id: UUID) -> PageVersion | None: ...

    def lock_if_exists(self, page_id: UUID) -> PageVersion | None: ...

    def append(
        self, page_id: UUID, number: int, title: str, content: str, restored_from: int | None
    ) -> PageVersion: ...

    def list_versions(self, page_id: UUID) -> list[VersionSummary]: ...

    def version(self, page_id: UUID, number: int) -> PageVersion | None: ...


class AccountRepository(Protocol):
    def add_user(self, email: str, password_hash: str) -> User:
        """Raises EmailTakenError."""

    def find_credentials(self, email: str) -> tuple[User, str] | None: ...

    def add_session(self, token_hash: bytes, user_id: UUID, expires_at: datetime) -> None: ...

    def find_session_user(self, token_hash: bytes, now: datetime) -> User | None: ...

    def delete_session(self, token_hash: bytes) -> None: ...

    def record_failed_login(self, key: bytes, at: datetime) -> None: ...

    def count_failed_logins(self, key: bytes, since: datetime) -> int: ...

    def clear_failed_logins(self, key: bytes) -> None: ...


class SearchIndex(Protocol):
    def replace_chunks(
        self, page_id: UUID, chunks: list[Chunk], vectors: list[Vector] | None
    ) -> None: ...

    def find(
        self,
        owner_id: UUID,
        query: str,
        vector: Vector | None,
        notebook_id: UUID | None,
        limit: int,
    ) -> list[SearchHit]: ...


class Transaction(Protocol):
    @property
    def nodes(self) -> NodeRepository: ...

    @property
    def pages(self) -> PageRepository: ...

    @property
    def accounts(self) -> AccountRepository: ...

    @property
    def search(self) -> SearchIndex: ...

    @property
    def jobs(self) -> JobOutbox: ...


class TransactionFactory(Protocol):
    def __call__(self) -> AbstractContextManager[Transaction]:
        """Commits when the block succeeds, rolls back when it raises."""


class PasswordHasher(Protocol):
    def hash(self, password: str) -> str: ...

    def verify(self, password_hash: str, password: str) -> bool: ...


class Clock(Protocol):
    def __call__(self) -> datetime: ...


class EmbeddingUnavailableError(Exception):
    """The embedder cannot answer now."""


class EmbeddingProvider(Protocol):
    """Raises EmbeddingUnavailableError."""

    def embed_query(self, query: str) -> Vector: ...

    def embed_passages(self, passages: list[str]) -> list[Vector]: ...


class PageChunker(Protocol):
    def chunk(self, title: str, content: str) -> list[Chunk]:
        """At least one chunk, so that an empty page is found by its title."""


class IndexingObserver(Protocol):
    def indexed(self, lag_seconds: float) -> None: ...
