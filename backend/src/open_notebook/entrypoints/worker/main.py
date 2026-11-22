"""Composition root of the worker process."""

import signal
from threading import Event
from types import FrameType

from prometheus_client import start_http_server

from open_notebook.entrypoints.worker.loop import run
from open_notebook.infrastructure.build_info import publish_build_info
from open_notebook.infrastructure.database import DatabaseProbe, build_engine
from open_notebook.infrastructure.logging import configure_logging
from open_notebook.settings import Settings

SERVICE = "worker"


def main() -> None:
    settings = Settings()
    configure_logging(settings, SERVICE)
    publish_build_info(SERVICE, settings.version)
    stop = Event()

    def request_stop(_signal: int, _frame: FrameType | None) -> None:
        stop.set()

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    start_http_server(settings.worker_metrics_port)
    run(DatabaseProbe(build_engine(settings)), stop, settings.worker_poll_seconds)
