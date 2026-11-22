"""Composition root of the worker process."""

import signal
from datetime import timedelta
from threading import Event, Thread
from types import FrameType

from prometheus_client import REGISTRY, start_http_server

from open_notebook.application.jobs import JOB_KINDS
from open_notebook.bootstrap import build_cleanup, build_job_processor
from open_notebook.entrypoints.worker.cleanup_loop import run_cleanup
from open_notebook.entrypoints.worker.loop import Timing, WorkerLoop
from open_notebook.infrastructure.build_info import publish_build_info
from open_notebook.infrastructure.database import build_engine
from open_notebook.infrastructure.embedding_client import build_embeddings
from open_notebook.infrastructure.job_metrics import JobMetrics, QueueCollector
from open_notebook.infrastructure.logging import configure_logging
from open_notebook.infrastructure.postgres.job_signal import JobSignal
from open_notebook.infrastructure.postgres.jobs import PostgresJobStore
from open_notebook.settings import Settings

SERVICE = "worker"


def main() -> None:
    settings = Settings()
    configure_logging(settings, SERVICE)
    publish_build_info(SERVICE, settings.version)
    engine = build_engine(settings)
    REGISTRY.register(QueueCollector(engine))
    start_http_server(settings.worker_metrics_port)

    stop = Event()

    def request_stop(_signal: int, _frame: FrameType | None) -> None:
        stop.set()

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)

    store = PostgresJobStore(engine)
    processor = build_job_processor(
        engine, store, build_embeddings(settings.embedder_url), JobMetrics()
    )
    timing = Timing(timedelta(seconds=settings.job_lease_seconds), settings.worker_poll_seconds)

    def run_loop(kind: str) -> None:
        job_signal = JobSignal(settings)
        loop = WorkerLoop(
            kind,
            store,
            processor,
            job_signal,
            timing,
        )
        loop.run(stop)
        job_signal.close()

    threads = [Thread(target=run_loop, args=(kind,)) for kind in JOB_KINDS]
    threads.append(Thread(target=run_cleanup, args=(build_cleanup(engine), stop)))
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
