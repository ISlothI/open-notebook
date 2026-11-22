"""Job queue in PostgreSQL."""

from collections.abc import Mapping
from datetime import timedelta
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import Connection, Engine, func, text, update
from sqlalchemy.dialects.postgresql import insert

from open_notebook.application.jobs import Job
from open_notebook.infrastructure.postgres.tables import jobs

NOTIFICATION_CHANNEL = "jobs"

CLAIM = text("""
    UPDATE jobs SET state = 'running', attempts = attempts + 1, leased_until = now() + :lease
    WHERE id = (
        SELECT id FROM jobs
        WHERE (state = 'queued' AND run_after <= now())
           OR (state = 'running' AND leased_until < now())
        ORDER BY run_after
        LIMIT 1
        FOR UPDATE SKIP LOCKED
    )
    RETURNING id, kind, payload, attempts, request_id
""")


class PostgresJobOutbox:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def enqueue(self, kind: str, payload: Mapping[str, Any], dedupe_key: str | None = None) -> UUID:
        statement = insert(jobs).values(
            kind=kind,
            payload=dict(payload),
            dedupe_key=dedupe_key,
            request_id=structlog.contextvars.get_contextvars().get("request_id"),
        )
        # Updating instead of doing nothing locks the waiting job, so that no worker can take
        # it before this transaction commits and then miss its changes.
        job_id: UUID = self._connection.scalars(
            statement.on_conflict_do_update(
                index_elements=[jobs.c.dedupe_key],
                index_where=jobs.c.state == text("'queued'"),
                set_={
                    "run_after": func.least(jobs.c.run_after, func.now()),
                    "request_id": statement.excluded.request_id,
                },
            ).returning(jobs.c.id)
        ).one()
        self._connection.execute(text(f"NOTIFY {NOTIFICATION_CHANNEL}"))
        return job_id


class PostgresJobStore:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def claim(self, lease: timedelta) -> Job | None:
        with self._engine.begin() as connection:
            row = connection.execute(CLAIM, {"lease": lease}).one_or_none()
        if row is None:
            return None
        return Job(row.id, row.kind, row.payload, row.attempts, row.request_id)

    def extend_lease(self, job: Job, lease: timedelta) -> bool:
        return self._update_owned(job, leased_until=func.now() + lease)

    def succeed(self, job: Job) -> bool:
        return self._update_owned(
            job, state="succeeded", leased_until=None, finished_at=func.now(), error=None
        )

    def retry(self, job: Job, delay: timedelta, error: str) -> bool:
        return self._update_owned(job, leased_until=func.now() + delay, error=error)

    def bury(self, job: Job, error: str) -> bool:
        return self._update_owned(
            job, state="dead", leased_until=None, finished_at=func.now(), error=error
        )

    def _update_owned(self, job: Job, **values: Any) -> bool:  # noqa: ANN401 - column values
        """Does nothing when another worker has taken over the job in the meantime."""
        with self._engine.begin() as connection:
            result = connection.execute(
                update(jobs)
                .where(
                    jobs.c.id == job.id, jobs.c.state == "running", jobs.c.attempts == job.attempt
                )
                .values(**values)
            )
        return result.rowcount == 1
