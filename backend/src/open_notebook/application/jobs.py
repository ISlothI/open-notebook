"""Background jobs: what a job is and how one job is processed."""

import random
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Protocol
from uuid import UUID

import structlog

INDEX_PAGE = "index_page"

MAX_ATTEMPTS = 5
BASE_DELAY = timedelta(seconds=5)
MAX_DELAY = timedelta(minutes=2)

log = structlog.get_logger(__name__)


class TransientError(Exception):
    """A dependency is down; the job is retried until it recovers."""


@dataclass(frozen=True)
class Job:
    id: UUID
    kind: str
    payload: dict[str, Any]
    # Grows with every claim, so it also tells whether a worker still owns the job.
    attempt: int
    request_id: str | None


class JobOutbox(Protocol):
    """Enqueues inside the caller's transaction: no change without its job, and vice versa."""

    def enqueue(
        self, kind: str, payload: Mapping[str, Any], dedupe_key: str | None = None
    ) -> UUID: ...


class JobStore(Protocol):
    """Every method is a transaction of its own."""

    def claim(self, lease: timedelta) -> Job | None: ...

    def extend_lease(self, job: Job, lease: timedelta) -> bool:
        """Returns whether the worker still owns the job."""

    def succeed(self, job: Job) -> bool: ...

    def retry(self, job: Job, delay: timedelta, error: str) -> bool: ...

    def bury(self, job: Job, error: str) -> bool: ...


type JobHandler = Callable[[Job], None]


class JobObserver(Protocol):
    def finished(self, kind: str, outcome: str) -> None: ...


def retry_delay(attempt: int, jitter: Callable[[], float] = random.random) -> timedelta:
    """Exponential, capped, and spread so that jobs do not retry in lockstep."""
    delay = min(BASE_DELAY * 2 ** (attempt - 1), MAX_DELAY) if attempt < MAX_ATTEMPTS else MAX_DELAY
    return delay * (0.5 + jitter() / 2)


class JobProcessor:
    """Runs one claimed job and records its outcome."""

    def __init__(
        self, store: JobStore, handlers: Mapping[str, JobHandler], observer: JobObserver
    ) -> None:
        self._store = store
        self._handlers = handlers
        self._observer = observer

    def process(self, job: Job) -> None:
        with structlog.contextvars.bound_contextvars(
            job_id=str(job.id), job_kind=job.kind, request_id=job.request_id
        ):
            outcome = self._run(job)
            self._observer.finished(job.kind, outcome)
            log.info("job_finished", outcome=outcome, attempt=job.attempt)

    def _run(self, job: Job) -> str:
        handler = self._handlers.get(job.kind)
        if handler is None:
            self._store.bury(job, "unknown kind")
            return "dead"
        try:
            handler(job)
        except TransientError as error:
            log.warning("job_postponed", error=str(error))
            self._store.retry(job, retry_delay(job.attempt), str(error))
            return "postponed"
        except Exception as error:
            log.exception("job_failed")
            return self._handle_failure(job, type(error).__name__)
        return "succeeded" if self._store.succeed(job) else "lost"

    def _handle_failure(self, job: Job, error: str) -> str:
        if job.attempt >= MAX_ATTEMPTS:
            self._store.bury(job, error)
            return "dead"
        self._store.retry(job, retry_delay(job.attempt), error)
        return "failed"
