from collections.abc import Callable, Iterator
from datetime import timedelta
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from open_notebook.application.jobs import JOB_KINDS
from open_notebook.application.ports import EmbeddingProvider
from open_notebook.bootstrap import build_job_processor, build_services
from open_notebook.entrypoints.api.app import create_app
from open_notebook.infrastructure.database import DatabaseProbe, build_engine
from open_notebook.infrastructure.job_metrics import JobMetrics
from open_notebook.infrastructure.postgres.jobs import PostgresJobStore
from open_notebook.settings import Settings
from tests.fakes import FakeEmbeddings
from tests.integration.notebook_client import NotebookClient

BACKEND_ROOT = Path(__file__).parents[2]
LEASE = timedelta(seconds=30)


def empty_database(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE users, failed_logins, jobs CASCADE"))


def build_test_client(engine: Engine, embeddings: EmbeddingProvider) -> NotebookClient:
    app = create_app(DatabaseProbe(engine), build_services(engine, embeddings), version="test")
    return NotebookClient(TestClient(app, base_url="https://testserver"))


def build_job_runner(engine: Engine, embeddings: EmbeddingProvider) -> Callable[[], int]:
    """Plays the worker until no job is due; the result tells how many jobs ran."""
    store = PostgresJobStore(engine)
    processor = build_job_processor(engine, store, embeddings, JobMetrics())

    def run() -> int:
        count = 0
        for kind in JOB_KINDS:
            while job := store.claim(kind, LEASE):
                processor.process(job)
                count += 1
        return count

    return run


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    engine = build_engine(Settings())
    command.upgrade(Config(str(BACKEND_ROOT / "alembic.ini")), "head")
    yield engine
    engine.dispose()


@pytest.fixture
def embeddings() -> FakeEmbeddings:
    return FakeEmbeddings()


@pytest.fixture
def store(engine: Engine) -> PostgresJobStore:
    return PostgresJobStore(engine)


@pytest.fixture
def run_jobs(engine: Engine, embeddings: FakeEmbeddings) -> Callable[[], int]:
    return build_job_runner(engine, embeddings)


@pytest.fixture
def new_client(engine: Engine, embeddings: FakeEmbeddings) -> Callable[[], NotebookClient]:
    """Creates independent browsers talking to one api with an empty database."""
    empty_database(engine)
    return lambda: build_test_client(engine, embeddings)


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
