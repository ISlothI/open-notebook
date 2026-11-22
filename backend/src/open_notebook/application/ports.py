"""What the use cases need from the outside world."""

from contextlib import AbstractContextManager
from datetime import datetime
from typing import Protocol
from uuid import UUID

from open_notebook.application.jobs import JobOutbox
from open_notebook.domain.accounts import User
from open_notebook.domain.exports import Document, Export, ExportState, Snapshot
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


class ExportRepository(Protocol):
    def add(self, owner_id: UUID, item_id: UUID, snapshot: Snapshot) -> Export: ...

    def get(self, owner_id: UUID, export_id: UUID) -> Export | None: ...

    def list_of(self, owner_id: UUID) -> list[Export]: ...

    def find_unfinished(self, owner_id: UUID, item_id: UUID) -> Export | None: ...

    def start(self, export_id: UUID) -> Snapshot | None:
        """None when there is nothing left to do."""

    def report(self, export_id: UUID, progress: int) -> None: ...

    def fail(self, export_id: UUID) -> Export | None: ...


class ArtifactStore(Protocol):
    def store(self, export_id: UUID, artifact: bytes, expires_at: datetime) -> bool:
        """False when the export has been finished by somebody else."""

    def load(self, export_id: UUID) -> bytes | None: ...


class Housekeeping(Protocol):
    def purge_trash(self, trashed_before: datetime) -> int: ...

    def expire_artifacts(self, now: datetime) -> int: ...

    def delete_sessions(self, now: datetime) -> int: ...

    def delete_failed_logins(self, before: datetime) -> int: ...

    def delete_jobs(self, finished_before: datetime) -> int: ...


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

    @property
    def exports(self) -> ExportRepository: ...

    @property
    def artifacts(self) -> ArtifactStore: ...

    @property
    def housekeeping(self) -> Housekeeping: ...


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


class DocumentRenderer(Protocol):
    def render(self, document: Document) -> bytes: ...


class ExportObserver(Protocol):
    def export_finished(self, state: ExportState, seconds: float) -> None: ...
