import io
from collections.abc import Callable
from datetime import timedelta

import pytest
from pypdf import PdfReader
from sqlalchemy import Engine, text

from open_notebook.bootstrap import build_cleanup
from open_notebook.domain.exports import Document
from open_notebook.infrastructure.pdf import WeasyPrintRenderer
from open_notebook.infrastructure.postgres.jobs import PostgresJobStore
from tests.integration.notebook_client import Json, NotebookClient

type RunJobs = Callable[[], int]


def request(client: NotebookClient, item: Json) -> Json:
    response = client.http.post("/api/exports", json={"item_id": item["id"]})
    assert response.status_code == 202, response.text
    body: Json = response.json()
    return body


def status(client: NotebookClient, export: Json) -> Json:
    body: Json = client.http.get(f"/api/exports/{export['id']}").json()
    return body


def pdf_text(client: NotebookClient, export: Json) -> str:
    response = client.http.get(status(client, export)["download_url"])
    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "application/pdf"
    reader = PdfReader(io.BytesIO(response.content))
    return "\n".join(page.extract_text() for page in reader.pages)


def notebook_with_pages(client: NotebookClient) -> tuple[Json, Json]:
    notebook = client.create("notebook", "Könyv")
    section = client.create("section", "Section", notebook)
    page = client.create("page", "Page one", section)
    client.save(page, "Page one", "first text", base=1)
    client.create("page", "Page two", section)
    return notebook, page


def expire_leases(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(text("UPDATE jobs SET leased_until = now() - interval '1 s'"))


def make_due(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(text("UPDATE jobs SET run_after = now() WHERE state = 'queued'"))


def test_f3_notebook_is_exported(alice: NotebookClient, run_jobs: RunJobs) -> None:
    notebook, _ = notebook_with_pages(alice)
    export = request(alice, notebook)
    assert (export["state"], export["download_url"]) == ("queued", None)

    run_jobs()

    finished = status(alice, export)
    assert (finished["state"], finished["progress"]) == ("succeeded", 100)
    content = pdf_text(alice, export)
    assert all(word in content for word in ("Könyv", "Contents", "Page two", "first text"))
    response = alice.http.get(finished["download_url"])
    assert "filename*=UTF-8''K%C3%B6nyv.pdf" in response.headers["content-disposition"]


def test_page_is_exported(alice: NotebookClient, run_jobs: RunJobs) -> None:
    _, page = notebook_with_pages(alice)
    export = request(alice, page)
    run_jobs()

    assert "first text" in pdf_text(alice, export)


def test_export_shows_the_state_at_the_request(alice: NotebookClient, run_jobs: RunJobs) -> None:
    _, page = notebook_with_pages(alice)
    export = request(alice, page)
    alice.save(page, "Page one", "later text", base=2)
    run_jobs()

    content = pdf_text(alice, export)
    assert "first text" in content
    assert "later text" not in content


def test_repeated_request_returns_the_running_export(
    alice: NotebookClient, run_jobs: RunJobs
) -> None:
    notebook, _ = notebook_with_pages(alice)
    first = request(alice, notebook)
    assert request(alice, notebook)["id"] == first["id"]

    run_jobs()
    assert request(alice, notebook)["id"] != first["id"]


def test_folders_sections_and_empty_notebooks_cannot_be_exported(alice: NotebookClient) -> None:
    folder = alice.create("folder", "F")
    notebook = alice.create("notebook", "N")
    section = alice.create("section", "S", notebook)
    for item in (folder, notebook, section):
        response = alice.http.post("/api/exports", json={"item_id": item["id"]})
        assert response.status_code == 422, item["kind"]


def test_exports_are_private(alice: NotebookClient, bob: NotebookClient, run_jobs: RunJobs) -> None:
    notebook, _ = notebook_with_pages(alice)
    export = request(alice, notebook)
    run_jobs()

    assert bob.http.get(f"/api/exports/{export['id']}").status_code == 404
    assert bob.http.get(f"/api/exports/{export['id']}/download").status_code == 404
    assert bob.http.get("/api/exports").json() == []
    assert bob.http.post("/api/exports", json={"item_id": notebook["id"]}).status_code == 404
    assert len(alice.http.get("/api/exports").json()) == 1


def test_r1_export_of_a_crashed_worker_is_finished_once(
    alice: NotebookClient,
    run_jobs: RunJobs,
    engine: Engine,
    store: PostgresJobStore,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    notebook, _ = notebook_with_pages(alice)
    run_jobs()
    export = request(alice, notebook)

    class WorkerKilledError(BaseException):
        """Not an ordinary exception: nothing in the process can handle being killed."""

    def die(_renderer: WeasyPrintRenderer, _document: Document) -> bytes:
        raise WorkerKilledError

    with monkeypatch.context() as patch, pytest.raises(WorkerKilledError):
        patch.setattr(WeasyPrintRenderer, "render", die)
        run_jobs()
    assert status(alice, export)["state"] == "running"
    assert run_jobs() == 0, "the lease still protects the job"

    expire_leases(engine)
    assert run_jobs() == 1

    assert status(alice, export)["state"] == "succeeded"
    assert "first text" in pdf_text(alice, export)
    assert store.claim("export_pdf", timedelta(seconds=1)) is None


def test_failing_export_is_reported_after_the_last_attempt(
    alice: NotebookClient, run_jobs: RunJobs, engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, page = notebook_with_pages(alice)
    run_jobs()
    export = request(alice, page)

    def fail(_renderer: WeasyPrintRenderer, _document: Document) -> bytes:
        raise ValueError

    monkeypatch.setattr(WeasyPrintRenderer, "render", fail)
    for _ in range(3):
        assert run_jobs() == 1
        make_due(engine)

    assert status(alice, export)["state"] == "failed"
    assert status(alice, export)["download_url"] is None


def test_too_large_document_fails(
    alice: NotebookClient, run_jobs: RunJobs, engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("open_notebook.application.exports.MAX_ARTIFACT_BYTES", 10)
    _, page = notebook_with_pages(alice)
    export = request(alice, page)
    for _ in range(3):
        run_jobs()
        make_due(engine)

    assert status(alice, export)["state"] == "failed"


def test_export_of_a_purged_page_ends_quietly(
    alice: NotebookClient, run_jobs: RunJobs, engine: Engine
) -> None:
    _, page = notebook_with_pages(alice)
    request(alice, page)
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM nodes"))

    run_jobs()

    with engine.connect() as connection:
        assert set(connection.scalars(text("SELECT state FROM jobs"))) == {"succeeded"}


def test_expired_file_is_not_served_and_then_removed(
    alice: NotebookClient, run_jobs: RunJobs, engine: Engine
) -> None:
    _, page = notebook_with_pages(alice)
    export = request(alice, page)
    run_jobs()
    with engine.begin() as connection:
        connection.execute(text("UPDATE exports SET expires_at = now() - interval '1 s'"))

    assert alice.http.get(f"/api/exports/{export['id']}/download").status_code == 404
    build_cleanup(engine)()

    assert status(alice, export)["state"] == "expired"
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT count(artifact) FROM exports")) == 0


def test_cleanup_removes_only_what_is_old(
    alice: NotebookClient, run_jobs: RunJobs, engine: Engine
) -> None:
    old, new = alice.create("notebook", "Old"), alice.create("notebook", "New")
    alice.create("section", "Inside", old)
    for item in (old, new):
        alice.trash(item)
    alice.create_page()
    run_jobs()
    with engine.begin() as connection:
        connection.execute(
            text("UPDATE nodes SET trashed_at = now() - interval '31 days' WHERE title = 'Old'")
        )
        connection.execute(text("UPDATE jobs SET finished_at = now() - interval '8 days'"))
        connection.execute(
            text("INSERT INTO failed_logins (key, at) VALUES ('\\x00', now() - interval '1 day')")
        )

    build_cleanup(engine)()

    assert alice.trashed_titles() == ["New"]
    assert "Page" in alice.titles()
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM nodes WHERE title = 'Inside'")) == 0
        assert connection.scalar(text("SELECT count(*) FROM jobs")) == 0
        assert connection.scalar(text("SELECT count(*) FROM failed_logins")) == 0
    assert alice.http.get("/api/auth/me").status_code == 200


def test_handler_is_idempotent(alice: NotebookClient, run_jobs: RunJobs, engine: Engine) -> None:
    _, page = notebook_with_pages(alice)
    export = request(alice, page)
    run_jobs()
    before = status(alice, export)
    with engine.begin() as connection:
        connection.execute(
            text("UPDATE jobs SET state = 'queued', run_after = now() WHERE kind = 'export_pdf'")
        )

    assert run_jobs() == 1
    assert status(alice, export) == before
