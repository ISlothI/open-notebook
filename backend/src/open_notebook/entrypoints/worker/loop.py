"""The worker's main loop, independent of signals and configuration."""

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import timedelta
from threading import Event, Thread
from typing import Protocol

import structlog
from prometheus_client import Gauge, Histogram

from open_notebook.application.jobs import Job, JobProcessor, JobStore

HEARTBEAT = Gauge("worker_last_heartbeat_timestamp_seconds", "Last successful worker iteration")
DURATION = Histogram(
    "job_duration_seconds",
    "Job execution time",
    ["kind"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60, 120),
)
RENEWALS_PER_LEASE = 3

log = structlog.get_logger(__name__)


class Signal(Protocol):
    def wait(self, seconds: float, stop: Event) -> None:
        """Returns when a job may be available, after `seconds` at the latest."""


@dataclass(frozen=True)
class Timing:
    lease: timedelta
    poll_seconds: float


class WorkerLoop:
    """Processes one kind of job, so that a flood of one kind cannot delay the others."""

    def __init__(
        self,
        kind: str,
        store: JobStore,
        processor: JobProcessor,
        signal: Signal,
        timing: Timing,
    ) -> None:
        self._kind = kind
        self._store = store
        self._processor = processor
        self._signal = signal
        self._lease = timing.lease
        self._poll_seconds = timing.poll_seconds

    def run(self, stop: Event) -> None:
        """Runs until `stop` is set; a job that has started is finished first."""
        log.info("worker_started", kind=self._kind)
        while not stop.is_set():
            if not self._process_next():
                self._signal.wait(self._poll_seconds, stop)
        log.info("worker_stopped", kind=self._kind)

    def _process_next(self) -> bool:
        try:
            job = self._store.claim(self._kind, self._lease)
            HEARTBEAT.set_to_current_time()
            if job is None:
                return False
            with DURATION.labels(job.kind).time(), self._lease_kept(job):
                self._processor.process(job)
        except Exception:
            # Most likely a database outage; the lease makes sure that no job is lost.
            log.exception("worker_iteration_failed")
            return False
        return True

    @contextmanager
    def _lease_kept(self, job: Job) -> Iterator[None]:
        done = Event()

        def renew() -> None:
            while not done.wait(self._lease.total_seconds() / RENEWALS_PER_LEASE):
                try:
                    owned = self._store.extend_lease(job, self._lease)
                except Exception:
                    log.exception("lease_renewal_failed", job_id=str(job.id))
                    continue
                if not owned:
                    log.warning("lease_lost", job_id=str(job.id))
                    return

        thread = Thread(target=renew, daemon=True)
        thread.start()
        try:
            yield
        finally:
            done.set()
            thread.join()
