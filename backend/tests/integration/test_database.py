from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, text

from open_notebook.infrastructure.database import DatabaseProbe, build_engine
from open_notebook.settings import Settings

BACKEND_ROOT = Path(__file__).parents[2]


@pytest.fixture
def engine() -> Iterator[Engine]:
    engine = build_engine(Settings())
    yield engine
    engine.dispose()


def extensions(engine: Engine) -> set[str]:
    with engine.connect() as connection:
        return set(connection.scalars(text("SELECT extname FROM pg_extension")))


def test_migrations_run_up_and_down(engine: Engine) -> None:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))

    command.upgrade(config, "head")
    assert {"vector", "unaccent"} <= extensions(engine)

    command.downgrade(config, "base")
    assert not {"vector", "unaccent"} & extensions(engine)

    command.upgrade(config, "head")
    command.upgrade(config, "head")


def test_probe_reports_running_database(engine: Engine) -> None:
    assert DatabaseProbe(engine).is_available()


def test_probe_reports_outage_without_raising() -> None:
    unreachable = create_engine(
        "postgresql+psycopg://nobody@127.0.0.1:1/none", connect_args={"connect_timeout": 1}
    )

    assert not DatabaseProbe(unreachable).is_available()
