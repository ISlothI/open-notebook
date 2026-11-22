"""Hierarchy storage."""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import Connection, RowMapping, func, insert, select, text, update

from open_notebook.domain.library import Node, NodeKind
from open_notebook.infrastructure.postgres.tables import nodes, users

NODE_COLUMNS = (
    nodes.c.id,
    nodes.c.kind,
    nodes.c.parent_id,
    nodes.c.title,
    nodes.c.position,
    nodes.c.created_at,
    nodes.c.trashed_at,
)

TRASH_SUBTREE = text("""
    WITH RECURSIVE subtree AS (
        SELECT id FROM nodes WHERE id = :node_id
        UNION ALL
        SELECT child.id FROM nodes child JOIN subtree ON child.parent_id = subtree.id
    )
    UPDATE nodes SET trashed_at = now(), trash_root_id = :node_id
    WHERE id IN (SELECT id FROM subtree) AND trashed_at IS NULL
""")

IS_INSIDE = text("""
    WITH RECURSIVE ancestors AS (
        SELECT id, parent_id FROM nodes WHERE id = :node_id
        UNION ALL
        SELECT parent.id, parent.parent_id
        FROM nodes parent JOIN ancestors ON parent.id = ancestors.parent_id
    )
    SELECT EXISTS (SELECT 1 FROM ancestors WHERE id = :ancestor_id)
""")


def to_node(row: RowMapping) -> Node:
    return Node(
        id=row["id"],
        kind=NodeKind(row["kind"]),
        parent_id=row["parent_id"],
        title=row["title"],
        position=row["position"],
        created_at=row["created_at"],
        trashed_at=row["trashed_at"],
    )


class PostgresNodes:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def lock_tree(self, owner_id: UUID) -> None:
        self._connection.execute(
            select(users.c.id).where(users.c.id == owner_id).with_for_update(key_share=True)
        )

    def list_active(self, owner_id: UUID) -> list[Node]:
        rows = self._connection.execute(
            select(*NODE_COLUMNS)
            .where(nodes.c.owner_id == owner_id, nodes.c.trashed_at.is_(None))
            .order_by(nodes.c.position, nodes.c.id)
        ).mappings()
        return [to_node(row) for row in rows]

    def list_trash(self, owner_id: UUID) -> list[Node]:
        rows = self._connection.execute(
            select(*NODE_COLUMNS)
            .where(nodes.c.owner_id == owner_id, nodes.c.trash_root_id == nodes.c.id)
            .order_by(nodes.c.trashed_at.desc(), nodes.c.id)
        ).mappings()
        return [to_node(row) for row in rows]

    def get(self, owner_id: UUID, node_id: UUID) -> Node | None:
        row = (
            self._connection.execute(
                select(*NODE_COLUMNS).where(nodes.c.id == node_id, nodes.c.owner_id == owner_id)
            )
            .mappings()
            .one_or_none()
        )
        return to_node(row) if row else None

    def add(self, owner_id: UUID, kind: NodeKind, parent: Node | None, title: str) -> Node:
        next_position = (
            select(func.coalesce(func.max(nodes.c.position) + 1, 0))
            .where(
                nodes.c.owner_id == owner_id,
                nodes.c.parent_id.is_not_distinct_from(parent.id if parent else None),
            )
            .scalar_subquery()
        )
        row = (
            self._connection.execute(
                insert(nodes)
                .values(
                    owner_id=owner_id,
                    kind=kind,
                    parent_id=parent.id if parent else None,
                    parent_kind=parent.kind if parent else None,
                    title=title,
                    position=next_position,
                )
                .returning(*NODE_COLUMNS)
            )
            .mappings()
            .one()
        )
        return to_node(row)

    def rename(self, node_id: UUID, title: str) -> None:
        self._connection.execute(update(nodes).where(nodes.c.id == node_id).values(title=title))

    def place(self, node: Node, parent: Node | None, position: int, owner_id: UUID) -> None:
        self._connection.execute(
            update(nodes)
            .where(nodes.c.id == node.id)
            .values(
                parent_id=parent.id if parent else None,
                parent_kind=parent.kind if parent else None,
            )
        )
        order = [
            sibling_id
            for sibling_id in self._active_children(owner_id, parent)
            if sibling_id != node.id
        ]
        order.insert(position, node.id)
        self._write_positions(order)

    def is_inside(self, node_id: UUID, ancestor_id: UUID) -> bool:
        found = self._connection.scalar(IS_INSIDE, {"node_id": node_id, "ancestor_id": ancestor_id})
        return bool(found)

    def is_trash_root(self, node_id: UUID) -> bool:
        root_id = self._connection.scalar(
            select(nodes.c.trash_root_id).where(nodes.c.id == node_id)
        )
        return root_id == node_id

    def trash(self, node_id: UUID) -> None:
        self._connection.execute(TRASH_SUBTREE, {"node_id": node_id})

    def restore(self, node_id: UUID) -> None:
        self._connection.execute(
            update(nodes)
            .where(nodes.c.trash_root_id == node_id)
            .values(trashed_at=None, trash_root_id=None)
        )

    def _active_children(self, owner_id: UUID, parent: Node | None) -> Sequence[UUID]:
        return self._connection.scalars(
            select(nodes.c.id)
            .where(
                nodes.c.owner_id == owner_id,
                nodes.c.parent_id.is_not_distinct_from(parent.id if parent else None),
                nodes.c.trashed_at.is_(None),
            )
            .order_by(nodes.c.position, nodes.c.id)
        ).all()

    def _write_positions(self, order: list[UUID]) -> None:
        self._connection.execute(
            text("""
                UPDATE nodes SET position = ordered.position - 1
                FROM unnest(CAST(:ids AS uuid[])) WITH ORDINALITY AS ordered (id, position)
                WHERE nodes.id = ordered.id
            """),
            {"ids": order},
        )
