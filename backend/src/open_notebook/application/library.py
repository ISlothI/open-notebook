"""Use cases of the hierarchy and the trash."""

from uuid import UUID

import structlog

from open_notebook.application.access import require_active_node
from open_notebook.application.pages import save_version
from open_notebook.application.ports import Transaction, TransactionFactory
from open_notebook.domain.errors import InvalidHierarchyError, NotFoundError, ParentTrashedError
from open_notebook.domain.library import Node, NodeKind, clean_title, ensure_placement

log = structlog.get_logger(__name__)


class LibraryService:
    def __init__(self, transactions: TransactionFactory) -> None:
        self._transactions = transactions

    def list_items(self, owner_id: UUID) -> list[Node]:
        with self._transactions() as tx:
            return tx.nodes.list_active(owner_id)

    def create(self, owner_id: UUID, kind: NodeKind, parent_id: UUID | None, title: str) -> Node:
        cleaned = clean_title(title)
        with self._transactions() as tx:
            tx.nodes.lock_tree(owner_id)
            parent = self._find_parent(tx, owner_id, parent_id)
            ensure_placement(kind, parent.kind if parent else None)
            node = tx.nodes.add(owner_id, kind, parent, cleaned)
            if kind is NodeKind.PAGE:
                tx.pages.create(node.id, cleaned)
        log.info("item_created", node_id=str(node.id), kind=kind)
        return node

    def rename(self, owner_id: UUID, node_id: UUID, title: str) -> Node:
        cleaned = clean_title(title)
        with self._transactions() as tx:
            node = require_active_node(tx, owner_id, node_id)
            if node.kind is NodeKind.PAGE:
                # The title belongs to the page's content, so renaming is a save as well.
                current = tx.pages.lock(node.id)
                save_version(tx, current, cleaned, current.content)
            else:
                tx.nodes.rename(node.id, cleaned)
            return require_active_node(tx, owner_id, node_id)

    def move(self, owner_id: UUID, node_id: UUID, parent_id: UUID | None, position: int) -> Node:
        with self._transactions() as tx:
            tx.nodes.lock_tree(owner_id)
            node = require_active_node(tx, owner_id, node_id)
            self._place(tx, owner_id, node, parent_id, position)
            return require_active_node(tx, owner_id, node_id)

    def trash(self, owner_id: UUID, node_id: UUID) -> None:
        with self._transactions() as tx:
            tx.nodes.lock_tree(owner_id)
            node = require_active_node(tx, owner_id, node_id)
            tx.nodes.trash(node.id)
        log.info("item_trashed", node_id=str(node_id), kind=node.kind)

    def list_trash(self, owner_id: UUID) -> list[Node]:
        with self._transactions() as tx:
            return tx.nodes.list_trash(owner_id)

    def restore(self, owner_id: UUID, node_id: UUID, parent_id: UUID | None = None) -> Node:
        """Restores to the original place, or to `parent_id` when it is given."""
        with self._transactions() as tx:
            tx.nodes.lock_tree(owner_id)
            node = tx.nodes.get(owner_id, node_id)
            if node is None or not tx.nodes.is_trash_root(node.id):
                raise NotFoundError("The item is not in the trash.")
            if parent_id is None:
                self._ensure_parent_is_active(tx, owner_id, node)
            tx.nodes.restore(node.id)
            if parent_id is not None:
                self._place(tx, owner_id, node, parent_id, position=node.position)
            restored = require_active_node(tx, owner_id, node_id)
        log.info("item_restored", node_id=str(node_id), kind=node.kind)
        return restored

    @staticmethod
    def _find_parent(tx: Transaction, owner_id: UUID, parent_id: UUID | None) -> Node | None:
        return require_active_node(tx, owner_id, parent_id) if parent_id else None

    @staticmethod
    def _ensure_parent_is_active(tx: Transaction, owner_id: UUID, node: Node) -> None:
        if node.parent_id is None:
            return
        parent = tx.nodes.get(owner_id, node.parent_id)
        if parent is None or parent.is_trashed:
            raise ParentTrashedError("The original place is in the trash; choose another one.")

    def _place(
        self, tx: Transaction, owner_id: UUID, node: Node, parent_id: UUID | None, position: int
    ) -> None:
        parent = self._find_parent(tx, owner_id, parent_id)
        ensure_placement(node.kind, parent.kind if parent else None)
        if parent and tx.nodes.is_inside(parent.id, node.id):
            raise InvalidHierarchyError("An item cannot be placed inside itself.")
        tx.nodes.place(node, parent, position, owner_id)
