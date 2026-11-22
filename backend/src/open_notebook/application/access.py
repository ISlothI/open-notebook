"""Ownership and visibility checks shared by the use cases."""

from uuid import UUID

from open_notebook.application.ports import Transaction
from open_notebook.domain.errors import NotFoundError
from open_notebook.domain.library import Node, NodeKind


def require_active_node(tx: Transaction, owner_id: UUID, node_id: UUID) -> Node:
    """Foreign, missing and trashed items are indistinguishable to the caller."""
    node = tx.nodes.get(owner_id, node_id)
    if node is None or node.is_trashed:
        raise NotFoundError("The item does not exist.")
    return node


def require_active_page(tx: Transaction, owner_id: UUID, page_id: UUID) -> Node:
    node = require_active_node(tx, owner_id, page_id)
    if node.kind is not NodeKind.PAGE:
        raise NotFoundError("The page does not exist.")
    return node
