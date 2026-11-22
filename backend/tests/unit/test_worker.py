from datetime import timedelta
from threading import Event
from uuid import uuid4

from prometheus_client import REGISTRY

from open_notebook.application.jobs import Job, JobProcessor
from open_notebook.entrypoints.worker.loop import HEARTBEAT, Timing, WorkerLoop
from tests.unit.test_jobs import FakeStore, RecordingObserver


class StopAfterWaits:
    """Ends the loop when it has been idle the given number of times."""

    def __init__(self, waits: int) -> None:
        self._remaining = waits

    def wait(self, seconds: float, stop: Event) -> None:
        self._remaining -= 1
        if self._remaining == 0:
            stop.set()


def new_job() -> Job:
    return Job(uuid4(), "work", {}, 1, 0, None)


def run_loop(
    store: FakeStore,
    handled: list[Job],
    waits: int = 1,
    lease: float = 30,
    delay: Event | None = None,
) -> None:
    def handle(job: Job) -> None:
        handled.append(job)
        if delay:
            delay.wait(0.5)

    processor = JobProcessor(store, {"work": handle}, RecordingObserver())
    loop = WorkerLoop(
        "work", store, processor, StopAfterWaits(waits), Timing(timedelta(seconds=lease), 0)
    )
    loop.run(Event())


def heartbeat() -> float:
    return REGISTRY.get_sample_value("worker_last_heartbeat_timestamp_seconds") or 0


def test_all_waiting_jobs_are_processed_before_idling() -> None:
    jobs = [new_job(), new_job()]
    handled: list[Job] = []

    run_loop(FakeStore(list(jobs)), handled)

    assert handled == jobs


def test_heartbeat_is_recorded_when_database_answers() -> None:
    HEARTBEAT.set(0)
    run_loop(FakeStore([]), [])
    assert heartbeat() > 0


def test_loop_survives_a_database_outage() -> None:
    HEARTBEAT.set(0)
    store = FakeStore([new_job()])
    store.claim_failures = 1
    handled: list[Job] = []

    run_loop(store, handled, waits=2)

    assert len(handled) == 1


def test_no_heartbeat_while_database_is_down() -> None:
    HEARTBEAT.set(0)
    store = FakeStore([])
    store.claim_failures = 1

    run_loop(store, [])

    assert heartbeat() == 0


def test_lease_of_a_long_job_is_renewed() -> None:
    store = FakeStore([new_job()])

    run_loop(store, [], lease=0.1, delay=Event())

    assert store.renewals > 1


def test_loop_ends_immediately_when_stop_is_requested() -> None:
    stop = Event()
    stop.set()
    handled: list[Job] = []
    processor = JobProcessor(FakeStore([new_job()]), {}, RecordingObserver())
    WorkerLoop(
        "work", FakeStore([new_job()]), processor, StopAfterWaits(1), Timing(timedelta(1), 60)
    ).run(stop)
    assert handled == []
