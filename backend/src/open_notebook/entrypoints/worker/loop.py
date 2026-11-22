"""The worker's main loop, independent of signals and configuration."""

from threading import Event
from typing import Protocol

import structlog
from prometheus_client import Gauge

HEARTBEAT = Gauge("worker_last_heartbeat_timestamp_seconds", "Last successful worker iteration")

log = structlog.get_logger(__name__)


class AvailabilityProbe(Protocol):
    def is_available(self) -> bool: ...


def run(database: AvailabilityProbe, stop: Event, poll_seconds: float) -> None:
    """Runs until `stop` is set. Job processing is added with the first job type."""
    log.info("worker_started")
    while not stop.is_set():
        if database.is_available():
            HEARTBEAT.set_to_current_time()
        stop.wait(poll_seconds)
    log.info("worker_stopped")
