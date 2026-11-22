from threading import Event

from prometheus_client import REGISTRY

from open_notebook.entrypoints.worker.loop import HEARTBEAT, run


class ProbeThatStops:
    """Stops the loop after the first iteration."""

    def __init__(self, available: bool, stop: Event) -> None:
        self._available = available
        self._stop = stop

    def is_available(self) -> bool:
        self._stop.set()
        return self._available


def heartbeat_after_one_iteration(available: bool) -> float | None:
    HEARTBEAT.set(0)
    stop = Event()
    run(ProbeThatStops(available, stop), stop, poll_seconds=0)
    return REGISTRY.get_sample_value("worker_last_heartbeat_timestamp_seconds")


def test_heartbeat_is_recorded_when_database_answers() -> None:
    assert (heartbeat_after_one_iteration(available=True) or 0) > 0


def test_no_heartbeat_while_database_is_down() -> None:
    assert heartbeat_after_one_iteration(available=False) == 0


def test_loop_ends_immediately_when_stop_is_requested() -> None:
    stop = Event()
    stop.set()

    run(ProbeThatStops(True, stop), stop, poll_seconds=60)
