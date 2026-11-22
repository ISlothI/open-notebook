"""PostgreSQL connection handling."""

import structlog
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from open_notebook.settings import Settings

CONNECT_TIMEOUT_SECONDS = 2
POOL_TIMEOUT_SECONDS = 3

log = structlog.get_logger(__name__)


def build_engine(settings: Settings) -> Engine:
    return create_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_timeout=POOL_TIMEOUT_SECONDS,
        connect_args={"connect_timeout": CONNECT_TIMEOUT_SECONDS},
        hide_parameters=True,
    )


class DatabaseProbe:
    """Tells whether the database answers; never raises for an outage."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def is_available(self) -> bool:
        try:
            with self._engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except SQLAlchemyError as error:
            log.warning("database_unavailable", error_type=type(error).__name__)
            return False
        return True
