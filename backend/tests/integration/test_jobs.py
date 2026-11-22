import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Event, Thread

import pytest
from sqlalchemy import Engine, text

from open_notebook.application.jobs import Job
from open_notebook.infrastructure.job_metrics import QueueCollector
from open_notebook.infrastructure.postgres.job_signal import JobSignal
from open_notebook.infrastructure.postgres.jobs import PostgresJobOutbox, PostgresJobStore
from open_notebook.infrastructure.postgres.transaction import PostgresTransactions
from open_notebook.settings import Settings

LEASE = timedelta(seconds=30)
EXPIRED = timedelta(seconds=-1)


@pytest.fixture(autouse=True)
def _empty_queue(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE jobs"))


@pytest.fixture
def enqueue(engine: Engine) -> Callable[..., None]:
    def run(kind: str = "work", dedupe_key: str | None = None) -> None:
        with engine.begin() as connection:
            PostgresJobOutbox(connection).enqueue(kind, {"n": 1}, dedupe_key)

    return run


def states(engine: Engine) -> list[str]:
    with engine.connect() as connection:
        return list(connection.scalars(text("SELECT state FROM jobs ORDER BY id")))


def claim(store: PostgresJobStore, lease: timedelta = LEASE) -> Job:
    job = store.claim(lease)
    assert job is not None
    return job


def test_job_is_claimed_once(store: PostgresJobStore, enqueue: Callable[..., None]) -> None:
    enqueue()

    assert claim(store).payload == {"n": 1}
    assert store.claim(LEASE) is None


def test_concurrent_workers_never_share_a_job(
    store: PostgresJobStore, enqueue: Callable[..., None]
) -> None:
    for _ in range(20):
        enqueue()

    with ThreadPoolExecutor(max_workers=8) as pool:
        claimed = [job for job in pool.map(lambda _: store.claim(LEASE), range(40)) if job]

    assert len(claimed) == len({job.id for job in claimed}) == 20


def test_rolled_back_change_leaves_no_job(engine: Engine, store: PostgresJobStore) -> None:
    with pytest.raises(RuntimeError), PostgresTransactions(engine)() as tx:
        tx.jobs.enqueue("work", {})
        raise RuntimeError

    assert store.claim(LEASE) is None


def test_job_of_a_dead_worker_is_taken_over(
    store: PostgresJobStore, enqueue: Callable[..., None]
) -> None:
    enqueue()
    lost = claim(store, EXPIRED)

    taken = claim(store)

    assert (taken.id, taken.attempt) == (lost.id, lost.attempt + 1)


def test_worker_that_lost_its_job_cannot_change_it(
    engine: Engine, store: PostgresJobStore, enqueue: Callable[..., None]
) -> None:
    enqueue()
    lost = claim(store, EXPIRED)
    taken = claim(store)

    assert not store.extend_lease(lost, LEASE)
    assert not store.succeed(lost)
    assert not store.bury(lost, "x")
    assert store.extend_lease(taken, LEASE)
    assert store.succeed(taken)
    assert states(engine) == ["succeeded"]


def test_renewed_lease_protects_the_job(
    store: PostgresJobStore, enqueue: Callable[..., None]
) -> None:
    enqueue()
    job = claim(store, EXPIRED)
    assert store.extend_lease(job, LEASE)

    assert store.claim(LEASE) is None


def test_retry_waits_for_its_delay(store: PostgresJobStore, enqueue: Callable[..., None]) -> None:
    enqueue()
    store.retry(claim(store), timedelta(seconds=0.5), "reason")

    assert store.claim(LEASE) is None
    time.sleep(0.6)
    assert claim(store).attempt == 2


def test_waiting_jobs_with_the_same_key_are_merged(
    engine: Engine, store: PostgresJobStore, enqueue: Callable[..., None]
) -> None:
    enqueue(dedupe_key="k")
    enqueue(dedupe_key="k")
    assert states(engine) == ["queued"]

    claim(store)
    enqueue(dedupe_key="k")
    assert states(engine) == ["running", "queued"]


def test_merged_job_cannot_start_before_the_merging_transaction_commits(
    engine: Engine, store: PostgresJobStore, enqueue: Callable[..., None]
) -> None:
    enqueue(dedupe_key="k")
    with engine.begin() as connection:
        PostgresJobOutbox(connection).enqueue("work", {}, "k")
        assert store.claim(LEASE) is None

    claim(store)


def test_signal_wakes_an_idle_worker(enqueue: Callable[..., None]) -> None:
    signal, stop, woken = JobSignal(Settings()), Event(), Event()
    signal.wait(0.1, stop)

    def wait() -> None:
        signal.wait(10, stop)
        woken.set()

    waiting = Thread(target=wait)
    waiting.start()
    time.sleep(0.2)
    enqueue()

    assert woken.wait(2)
    waiting.join()
    signal.close()


def test_queue_metrics(
    engine: Engine, store: PostgresJobStore, enqueue: Callable[..., None]
) -> None:
    enqueue()
    enqueue()
    claim(store)

    depth, age = QueueCollector(engine).collect()

    assert {sample.labels["state"]: sample.value for sample in depth.samples} == {
        "queued": 1,
        "running": 1,
    }
    assert all(sample.value >= 0 for sample in age.samples)
