"""Wakes idle workers when a job arrives."""

from threading import Event

import psycopg

from open_notebook.infrastructure.database import CONNECT_TIMEOUT_SECONDS
from open_notebook.infrastructure.postgres.jobs import NOTIFICATION_CHANNEL
from open_notebook.settings import Settings


class JobSignal:
    """Listens on its own connection; without one, it degrades to polling."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._connection: psycopg.Connection | None = None

    def wait(self, seconds: float, stop: Event) -> None:
        try:
            for _ in self._connected().notifies(timeout=seconds, stop_after=1):
                return
        except psycopg.Error:
            self.close()
            stop.wait(seconds)

    def close(self) -> None:
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def _connected(self) -> psycopg.Connection:
        if self._connection is None:
            self._connection = psycopg.connect(
                host=self._settings.database_host,
                port=self._settings.database_port,
                dbname=self._settings.database_name,
                user=self._settings.database_user,
                password=self._settings.database_password.get_secret_value(),
                connect_timeout=CONNECT_TIMEOUT_SECONDS,
                autocommit=True,
            )
            self._connection.execute(f"LISTEN {NOTIFICATION_CHANNEL}")
        return self._connection
