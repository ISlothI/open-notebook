import subprocess
import sys
from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.dialects.postgresql.base import ischema_names

from open_notebook.infrastructure.database import DatabaseProbe
from open_notebook.infrastructure.postgres.tables import EmbeddingVector, metadata

BACKEND_ROOT = Path(__file__).parents[2]


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


def test_concurrent_migrations_wait_for_each_other(engine: Engine) -> None:
    command.downgrade(Config(str(BACKEND_ROOT / "alembic.ini")), "base")

    processes = [
        subprocess.Popen([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=BACKEND_ROOT)
        for _ in range(3)
    ]

    assert [process.wait(timeout=30) for process in processes] == [0, 0, 0]
    assert {"vector", "unaccent"} <= extensions(engine)


def test_probe_reports_running_database(engine: Engine) -> None:
    assert DatabaseProbe(engine).is_available()


def test_probe_reports_outage_without_raising() -> None:
    unreachable = create_engine(
        "postgresql+psycopg://nobody@127.0.0.1:1/none", connect_args={"connect_timeout": 1}
    )

    assert not DatabaseProbe(unreachable).is_available()


def test_migrations_and_table_definitions_agree(
    engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setitem(ischema_names, "vector", EmbeddingVector)
    with engine.connect() as connection:
        context = MigrationContext.configure(connection, opts={"compare_type": True})
        assert compare_metadata(context, metadata) == []
