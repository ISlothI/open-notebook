"""What the use cases need from the outside world."""

from contextlib import AbstractContextManager
from datetime import datetime
from typing import Protocol
from uuid import UUID

from open_notebook.domain.accounts import User
from open_notebook.domain.library import Node, NodeKind
from open_notebook.domain.pages import PageVersion, VersionSummary


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


class Transaction(Protocol):
    @property
    def nodes(self) -> NodeRepository: ...

    @property
    def pages(self) -> PageRepository: ...

    @property
    def accounts(self) -> AccountRepository: ...


class TransactionFactory(Protocol):
    def __call__(self) -> AbstractContextManager[Transaction]:
        """Commits when the block succeeds, rolls back when it raises."""


class PasswordHasher(Protocol):
    def hash(self, password: str) -> str: ...

    def verify(self, password_hash: str, password: str) -> bool: ...


class Clock(Protocol):
    def __call__(self) -> datetime: ...
