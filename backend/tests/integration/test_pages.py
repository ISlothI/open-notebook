from concurrent.futures import ThreadPoolExecutor

from open_notebook.domain.pages import MAX_CONTENT_BYTES
from tests.integration.notebook_client import NotebookClient


def test_every_save_creates_a_version(alice: NotebookClient) -> None:
    page = alice.create_page("Draft")

    assert alice.save(page, "Draft", "first", base=1)["version"] == 2
    assert alice.save(page, "Final", "second", base=2)["version"] == 3

    assert [item["version"] for item in alice.versions(page)] == [3, 2, 1]
    assert alice.read(page)["content"] == "second"
    assert "Final" in alice.titles()


def test_old_version_can_be_read_and_restored(alice: NotebookClient) -> None:
    page = alice.create_page("Draft")
    alice.save(page, "Draft", "first", base=1)
    alice.save(page, "Final", "second", base=2)
    versions = f"/api/pages/{page['id']}/versions"

    assert alice.http.get(f"{versions}/2").json()["content"] == "first"
    restored = alice.http.post(f"{versions}/2/restore").json()

    assert (restored["version"], restored["restored_from"]) == (4, 2)
    assert alice.read(page)["content"] == "first"
    assert "Draft" in alice.titles()
    # The text that was replaced is still there, so the restore can be undone.
    assert alice.http.get(f"{versions}/3").json()["content"] == "second"


def test_unknown_version(alice: NotebookClient) -> None:
    versions = f"/api/pages/{alice.create_page()['id']}/versions"

    assert alice.http.get(f"{versions}/99").status_code == 404
    assert alice.http.post(f"{versions}/99/restore").status_code == 404


def test_conflicting_save_overwrites_nothing(alice: NotebookClient) -> None:
    page = alice.create_page()
    alice.save(page, "Page", "from the first tab", base=1)

    response = alice.try_save(page, "Page", "from the second tab", base=1)

    assert response.status_code == 409
    body = response.json()
    assert body["code"] == "version_conflict"
    assert body["current"]["content"] == "from the first tab"
    assert body["current"]["version"] == 2
    assert alice.read(page)["content"] == "from the first tab"


def test_retried_save_is_not_a_conflict_and_not_a_new_version(alice: NotebookClient) -> None:
    page = alice.create_page()
    first = alice.save(page, "Page", "text", base=1)

    assert alice.save(page, "Page", "text", base=1) == first
    assert len(alice.versions(page)) == 2


def test_concurrent_saves_let_exactly_one_win(alice: NotebookClient) -> None:
    page = alice.create_page()

    with ThreadPoolExecutor(max_workers=5) as pool:
        statuses = list(
            pool.map(lambda n: alice.try_save(page, "Page", f"text {n}", 1).status_code, range(5))
        )

    assert sorted(statuses) == [200, 409, 409, 409, 409]
    assert len(alice.versions(page)) == 2


def test_content_limit(alice: NotebookClient) -> None:
    page = alice.create_page()

    response = alice.try_save(page, "Page", "x" * (MAX_CONTENT_BYTES + 1), base=1)

    assert response.status_code == 422
    assert response.json()["code"] == "invalid_value"


def test_notebook_is_not_a_page(alice: NotebookClient) -> None:
    notebook = alice.create("notebook", "Notebook")

    assert alice.http.get(f"/api/pages/{notebook['id']}").status_code == 404
