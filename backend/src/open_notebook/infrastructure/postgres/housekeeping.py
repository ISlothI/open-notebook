"""Deletion of outdated rows."""

from datetime import datetime

from sqlalchemy import Connection, delete, update

from open_notebook.domain.exports import ExportState
from open_notebook.infrastructure.postgres.tables import (
    exports,
    failed_logins,
    jobs,
    nodes,
    sessions,
)


class PostgresHousekeeping:
    """Every method returns the number of affected rows."""

    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def purge_trash(self, trashed_before: datetime) -> int:
        # Descendants are deleted by the foreign keys.
        statement = delete(nodes).where(
            nodes.c.trash_root_id == nodes.c.id, nodes.c.trashed_at < trashed_before
        )
        return self._connection.execute(statement).rowcount

    def expire_artifacts(self, now: datetime) -> int:
        statement = (
            update(exports)
            .where(exports.c.state == ExportState.SUCCEEDED, exports.c.expires_at <= now)
            .values(state=ExportState.EXPIRED, artifact=None)
        )
        return self._connection.execute(statement).rowcount

    def delete_sessions(self, now: datetime) -> int:
        return self._connection.execute(
            delete(sessions).where(sessions.c.expires_at <= now)
        ).rowcount

    def delete_failed_logins(self, before: datetime) -> int:
        return self._connection.execute(
            delete(failed_logins).where(failed_logins.c.at < before)
        ).rowcount

    def delete_jobs(self, finished_before: datetime) -> int:
        # Dead jobs stay, because somebody has to look at them.
        statement = delete(jobs).where(
            jobs.c.state == "succeeded", jobs.c.finished_at < finished_before
        )
        return self._connection.execute(statement).rowcount
