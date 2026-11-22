from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from open_notebook.bootstrap import build_services
from open_notebook.entrypoints.api.app import create_app
from open_notebook.infrastructure.database import DatabaseProbe, build_engine
from open_notebook.settings import Settings
from tests.integration.notebook_client import NotebookClient

BACKEND_ROOT = Path(__file__).parents[2]


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    engine = build_engine(Settings())
    command.upgrade(Config(str(BACKEND_ROOT / "alembic.ini")), "head")
    yield engine
    engine.dispose()


@pytest.fixture
def new_client(engine: Engine) -> Iterator[Callable[[], NotebookClient]]:
    """Creates independent browsers talking to one api with an empty database."""
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE users, failed_logins CASCADE"))
    app = create_app(DatabaseProbe(engine), build_services(engine), version="test")

    def build() -> NotebookClient:
        return NotebookClient(TestClient(app, base_url="https://testserver"))

    yield build


@pytest.fixture
def alice(new_client: Callable[[], NotebookClient]) -> NotebookClient:
    client = new_client()
    client.register("alice@example.test")
    return client


@pytest.fixture
def bob(new_client: Callable[[], NotebookClient]) -> NotebookClient:
    client = new_client()
    client.register("bob@example.test")
    return client
