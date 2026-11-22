"""Runs the cleanup from time to time."""

from collections.abc import Callable
from threading import Event

import structlog

INTERVAL_SECONDS = 600.0

log = structlog.get_logger(__name__)


def run_cleanup(
    cleanup: Callable[[], None], stop: Event, interval_seconds: float = INTERVAL_SECONDS
) -> None:
    while not stop.is_set():
        try:
            cleanup()
        except Exception:
            # The next round tries again.
            log.exception("cleanup_failed")
        stop.wait(interval_seconds)
