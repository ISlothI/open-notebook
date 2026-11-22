from threading import Event

from open_notebook.entrypoints.worker.cleanup_loop import run_cleanup


def test_cleanup_is_repeated_and_survives_failures() -> None:
    stop = Event()
    calls: list[int] = []

    def cleanup() -> None:
        calls.append(len(calls))
        if len(calls) == 1:
            raise ConnectionError
        stop.set()

    run_cleanup(cleanup, stop, interval_seconds=0)

    assert calls == [0, 1]
