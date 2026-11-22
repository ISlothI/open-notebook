"""Page and version storage."""

from uuid import UUID

from sqlalchemy import Connection, RowMapping, Select, insert, select, update

from open_notebook.domain.pages import FIRST_VERSION, PageVersion, VersionSummary
from open_notebook.infrastructure.postgres.tables import page_versions, pages


def to_version(row: RowMapping) -> PageVersion:
    return PageVersion(
        page_id=row["page_id"],
        number=row["number"],
        title=row["title"],
        content=row["content"],
        created_at=row["created_at"],
        restored_from=row["restored_from"],
    )


def select_current(page_id: UUID) -> Select[tuple[object, ...]]:
    return (
        select(*page_versions.c)
        .join(
            pages,
            (pages.c.node_id == page_versions.c.page_id)
            & (pages.c.current_number == page_versions.c.number),
        )
        .where(pages.c.node_id == page_id)
    )


class PostgresPages:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def create(self, page_id: UUID, title: str) -> None:
        self._connection.execute(
            insert(pages).values(node_id=page_id, current_number=FIRST_VERSION)
        )
        self._connection.execute(
            insert(page_versions).values(
                page_id=page_id, number=FIRST_VERSION, title=title, content=""
            )
        )

    def current(self, page_id: UUID) -> PageVersion:
        return to_version(self._connection.execute(select_current(page_id)).mappings().one())

    def lock(self, page_id: UUID) -> PageVersion:
        # Locking first and reading in a second statement sees what a waited-for save committed.
        self._connection.execute(
            select(pages.c.node_id).where(pages.c.node_id == page_id).with_for_update()
        )
        return self.current(page_id)

    def append(
        self, page_id: UUID, number: int, title: str, content: str, restored_from: int | None
    ) -> PageVersion:
        row = (
            self._connection.execute(
                insert(page_versions)
                .values(
                    page_id=page_id,
                    number=number,
                    title=title,
                    content=content,
                    restored_from=restored_from,
                )
                .returning(*page_versions.c)
            )
            .mappings()
            .one()
        )
        self._connection.execute(
            update(pages).where(pages.c.node_id == page_id).values(current_number=number)
        )
        return to_version(row)

    def list_versions(self, page_id: UUID) -> list[VersionSummary]:
        rows = self._connection.execute(
            select(
                page_versions.c.number,
                page_versions.c.title,
                page_versions.c.created_at,
                page_versions.c.restored_from,
            )
            .where(page_versions.c.page_id == page_id)
            .order_by(page_versions.c.number.desc())
        ).mappings()
        return [VersionSummary(**row) for row in rows]

    def version(self, page_id: UUID, number: int) -> PageVersion | None:
        row = (
            self._connection.execute(
                select(*page_versions.c).where(
                    page_versions.c.page_id == page_id, page_versions.c.number == number
                )
            )
            .mappings()
            .one_or_none()
        )
        return to_version(row) if row else None
