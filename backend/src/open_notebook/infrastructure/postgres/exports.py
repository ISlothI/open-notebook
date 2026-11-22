"""Export and artifact storage."""

from datetime import datetime
from uuid import UUID

from pydantic import TypeAdapter
from sqlalchemy import Connection, RowMapping, func, insert, select, update

from open_notebook.domain.exports import UNFINISHED, Export, ExportState, Snapshot
from open_notebook.infrastructure.postgres.tables import exports

RECENT_EXPORTS = 50
# The artifact is left out, because it can be large.
EXPORT_COLUMNS = (
    exports.c.id,
    exports.c.item_id,
    exports.c.title,
    exports.c.state,
    exports.c.progress,
    exports.c.created_at,
    exports.c.finished_at,
    exports.c.expires_at,
)
SNAPSHOT = TypeAdapter(Snapshot)


def to_export(row: RowMapping) -> Export:
    return Export(**dict(row) | {"state": ExportState(row["state"])})


class PostgresExports:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def add(self, owner_id: UUID, item_id: UUID, snapshot: Snapshot) -> Export:
        return to_export(
            self._connection.execute(
                insert(exports)
                .values(
                    owner_id=owner_id,
                    item_id=item_id,
                    title=snapshot.title,
                    snapshot=SNAPSHOT.dump_python(snapshot, mode="json"),
                )
                .returning(*EXPORT_COLUMNS)
            )
            .mappings()
            .one()
        )

    def get(self, owner_id: UUID, export_id: UUID) -> Export | None:
        row = (
            self._connection.execute(
                select(*EXPORT_COLUMNS).where(
                    exports.c.id == export_id, exports.c.owner_id == owner_id
                )
            )
            .mappings()
            .one_or_none()
        )
        return to_export(row) if row else None

    def list_of(self, owner_id: UUID) -> list[Export]:
        rows = self._connection.execute(
            select(*EXPORT_COLUMNS)
            .where(exports.c.owner_id == owner_id)
            .order_by(exports.c.created_at.desc())
            .limit(RECENT_EXPORTS)
        ).mappings()
        return [to_export(row) for row in rows]

    def find_unfinished(self, owner_id: UUID, item_id: UUID) -> Export | None:
        row = (
            self._connection.execute(
                select(*EXPORT_COLUMNS).where(
                    exports.c.owner_id == owner_id,
                    exports.c.item_id == item_id,
                    exports.c.state.in_(UNFINISHED),
                )
            )
            .mappings()
            .first()
        )
        return to_export(row) if row else None

    def start(self, export_id: UUID) -> Snapshot | None:
        row = self._connection.execute(
            update(exports)
            .where(exports.c.id == export_id, exports.c.state.in_(UNFINISHED))
            .values(state=ExportState.RUNNING, progress=0)
            .returning(exports.c.snapshot)
        ).one_or_none()
        return SNAPSHOT.validate_python(row.snapshot) if row else None

    def report(self, export_id: UUID, progress: int) -> None:
        self._connection.execute(
            update(exports)
            .where(exports.c.id == export_id, exports.c.state == ExportState.RUNNING)
            .values(progress=progress)
        )

    def fail(self, export_id: UUID) -> Export | None:
        row = (
            self._connection.execute(
                update(exports)
                .where(exports.c.id == export_id, exports.c.state.in_(UNFINISHED))
                .values(state=ExportState.FAILED, finished_at=func.now())
                .returning(*EXPORT_COLUMNS)
            )
            .mappings()
            .one_or_none()
        )
        return to_export(row) if row else None


class PostgresArtifacts:
    """Artifacts are small and short-lived, so they need no storage system of their own."""

    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def store(self, export_id: UUID, artifact: bytes, expires_at: datetime) -> bool:
        result = self._connection.execute(
            update(exports)
            .where(exports.c.id == export_id, exports.c.state == ExportState.RUNNING)
            .values(
                state=ExportState.SUCCEEDED,
                progress=100,
                artifact=artifact,
                finished_at=func.now(),
                expires_at=expires_at,
            )
        )
        return result.rowcount == 1

    def load(self, export_id: UUID) -> bytes | None:
        artifact: bytes | None = self._connection.scalar(
            select(exports.c.artifact).where(exports.c.id == export_id)
        )
        return artifact
