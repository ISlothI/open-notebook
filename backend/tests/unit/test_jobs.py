from collections.abc import Callable
from datetime import timedelta
from uuid import uuid4

import pytest

from open_notebook.application.jobs import (
    MAX_ATTEMPTS,
    MAX_CRASHES,
    MAX_DELAY,
    Job,
    JobProcessor,
    TransientError,
    retry_delay,
)


class FakeStore:
    def __init__(self, jobs: list[Job] | None = None) -> None:
        self.jobs = jobs or []
        self.outcomes: list[str] = []
        self.owned = True
        self.claim_failures = 0
        self.renewals = 0

    def claim(self, kind: str, lease: timedelta) -> Job | None:
        if self.claim_failures:
            self.claim_failures -= 1
            raise ConnectionError
        return self.jobs.pop(0) if self.jobs else None

    def extend_lease(self, job: Job, lease: timedelta) -> bool:
        self.renewals += 1
        return self.owned

    def succeed(self, job: Job) -> bool:
        return self._record("succeeded")

    def retry(self, job: Job, delay: timedelta, error: str) -> bool:
        return self._record("retried")

    def bury(self, job: Job, error: str) -> bool:
        return self._record("buried")

    def _record(self, outcome: str) -> bool:
        if self.owned:
            self.outcomes.append(outcome)
        return self.owned


class RecordingObserver:
    def __init__(self) -> None:
        self.outcomes: list[str] = []

    def finished(self, kind: str, outcome: str) -> None:
        self.outcomes.append(outcome)


def succeed(_job: Job) -> None:
    pass


def fail(_job: Job) -> None:
    raise ValueError


def postpone(_job: Job) -> None:
    raise TransientError("dependency down")


@pytest.mark.parametrize(
    ("handler", "attempt", "stored", "observed"),
    [
        (succeed, 1, "succeeded", "succeeded"),
        (fail, 1, "retried", "failed"),
        (fail, MAX_ATTEMPTS, "buried", "dead"),
        (postpone, 1, "retried", "postponed"),
        (postpone, MAX_ATTEMPTS * 10, "retried", "postponed"),
    ],
)
def test_outcomes(handler: Callable[[Job], None], attempt: int, stored: str, observed: str) -> None:
    store, observer = FakeStore(), RecordingObserver()

    JobProcessor(store, {"work": handler}, observer).process(
        Job(uuid4(), "work", {}, attempt, 0, None)
    )

    assert (store.outcomes, observer.outcomes) == ([stored], [observed])


def test_job_taken_over_by_another_worker_is_not_reported_as_success() -> None:
    store, observer = FakeStore(), RecordingObserver()
    store.owned = False

    JobProcessor(store, {"work": succeed}, observer).process(Job(uuid4(), "work", {}, 1, 0, None))

    assert observer.outcomes == ["lost"]


def test_retry_delay_grows_to_a_limit() -> None:
    delays = [retry_delay(attempt, jitter=lambda: 1.0) for attempt in (1, 2, 3, 4, 5, 500)]

    assert delays == sorted(delays)
    assert delays[0] == timedelta(seconds=5)
    assert delays[-1] == MAX_DELAY


def test_retry_delay_is_spread() -> None:
    assert retry_delay(1, jitter=lambda: 0.0) == retry_delay(1, jitter=lambda: 1.0) / 2


def test_job_that_keeps_crashing_its_worker_is_buried_without_running() -> None:
    store, observer = FakeStore(), RecordingObserver()
    told: list[Job] = []
    job = Job(uuid4(), "work", {}, 4, MAX_CRASHES, None)

    JobProcessor(store, {"work": fail}, observer, {"work": told.append}).process(job)

    assert (store.outcomes, observer.outcomes, told) == (["buried"], ["dead"], [job])
