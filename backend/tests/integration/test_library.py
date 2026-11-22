import uuid
from collections.abc import Callable

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import IntegrityError

from tests.integration.notebook_client import NotebookClient


def test_hierarchy_can_be_built(alice: NotebookClient) -> None:
    folder = alice.create("folder", "Studies")
    notebook = alice.create("notebook", "DevOps", alice.create("folder", "Autumn", folder))
    alice.create("page", "Lecture 1", alice.create("section", "Lectures", notebook))

    assert set(alice.titles()) == {"Studies", "Autumn", "DevOps", "Lectures", "Lecture 1"}


def test_invalid_placement_is_refused(alice: NotebookClient) -> None:
    folder = alice.create("folder", "Folder")
    response = alice.http.post(
        "/api/items", json={"kind": "page", "title": "Page", "parent_id": folder["id"]}
    )

    assert response.status_code == 422
    assert response.json()["code"] == "invalid_hierarchy"


def test_database_refuses_invalid_placement_even_if_code_is_wrong(
    alice: NotebookClient, engine: Engine
) -> None:
    section = alice.create("section", "S", alice.create("notebook", "N"))
    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(
            text("UPDATE nodes SET parent_id = NULL, parent_kind = NULL WHERE id = :id"),
            {"id": section["id"]},
        )


def test_items_can_be_reordered(alice: NotebookClient) -> None:
    for title in ("A", "B", "C"):
        alice.create("notebook", title)
    last = alice.http.get("/api/items").json()[-1]

    assert alice.move(last, None, position=1).status_code == 200

    assert alice.titles() == ["A", "C", "B"]


def test_item_can_be_moved_to_another_parent(alice: NotebookClient) -> None:
    folder = alice.create("folder", "Folder")
    notebook = alice.create("notebook", "Notebook")

    assert alice.move(notebook, folder).json()["parent_id"] == folder["id"]


def test_folder_cannot_be_moved_into_itself(alice: NotebookClient) -> None:
    outer = alice.create("folder", "Outer")
    inner = alice.create("folder", "Inner", outer)

    assert alice.move(outer, outer).status_code == 422
    assert alice.move(outer, inner).status_code == 422


def test_rename(alice: NotebookClient) -> None:
    notebook = alice.create("notebook", "Old")
    page = alice.create_page("Old page")

    alice.http.patch(f"/api/items/{notebook['id']}", json={"title": "New"})
    alice.http.patch(f"/api/items/{page['id']}", json={"title": "New page"})

    assert "New" in alice.titles()
    assert alice.read(page)["title"] == "New page"
    assert len(alice.versions(page)) == 2


def test_trash_hides_the_subtree_and_restore_brings_it_back(alice: NotebookClient) -> None:
    notebook = alice.create("notebook", "Notebook")
    page = alice.create("page", "Page", alice.create("section", "Section", notebook))
    alice.save(page, "Page", "precious", base=1)

    alice.trash(notebook)

    assert alice.titles() == []
    assert alice.trashed_titles() == ["Notebook"]
    assert alice.http.get(f"/api/pages/{page['id']}").status_code == 404
    assert alice.try_save(page, "Page", "x", 2).status_code == 404

    assert alice.restore(notebook).status_code == 200

    assert set(alice.titles()) == {"Notebook", "Section", "Page"}
    assert alice.trashed_titles() == []
    assert alice.read(page)["content"] == "precious"


@pytest.mark.parametrize("kind", ["folder", "notebook", "section", "page"])
def test_every_kind_can_be_trashed_and_restored(alice: NotebookClient, kind: str) -> None:
    items = {"folder": alice.create("folder", "folder")}
    items["notebook"] = alice.create("notebook", "notebook", items["folder"])
    items["section"] = alice.create("section", "section", items["notebook"])
    items["page"] = alice.create("page", "page", items["section"])

    alice.trash(items[kind])
    assert kind not in alice.titles()

    assert alice.restore(items[kind]).status_code == 200
    assert len(alice.titles()) == 4


def test_separately_trashed_child_stays_in_the_trash(alice: NotebookClient) -> None:
    notebook = alice.create("notebook", "Notebook")
    section = alice.create("section", "Section", notebook)
    alice.trash(section)
    alice.trash(notebook)

    alice.restore(notebook)

    assert alice.titles() == ["Notebook"]
    assert alice.trashed_titles() == ["Section"]


def test_restore_into_trashed_parent_needs_a_new_place(alice: NotebookClient) -> None:
    old, other = alice.create("notebook", "Old"), alice.create("notebook", "Other")
    section = alice.create("section", "Section", old)
    alice.trash(section)
    alice.trash(old)

    refused = alice.restore(section)
    assert refused.status_code == 409
    assert refused.json()["code"] == "parent_trashed"

    assert alice.restore(section, other).json()["parent_id"] == other["id"]
    assert set(alice.titles()) == {"Other", "Section"}


def test_only_trash_roots_can_be_restored(alice: NotebookClient) -> None:
    notebook = alice.create("notebook", "Notebook")
    section = alice.create("section", "Section", notebook)
    alice.trash(notebook)

    assert alice.restore(section).status_code == 404
    assert alice.restore({"id": str(uuid.uuid4())}).status_code == 404


def test_other_users_items_do_not_exist(alice: NotebookClient, bob: NotebookClient) -> None:
    page = alice.create_page()
    notebook = alice.create("notebook", "Private")
    trashed = alice.create("notebook", "Trashed")
    alice.trash(trashed)
    item = f"/api/items/{notebook['id']}"
    page_url = f"/api/pages/{page['id']}"

    attempts: list[Callable[[], int]] = [
        lambda: bob.http.patch(item, json={"title": "x"}).status_code,
        lambda: bob.http.delete(item).status_code,
        lambda: int(bob.move(notebook, None).status_code),
        lambda: int(bob.restore(trashed).status_code),
        lambda: bob.http.get(page_url).status_code,
        lambda: int(bob.try_save(page, "x", "x", 1).status_code),
        lambda: bob.http.get(f"{page_url}/versions").status_code,
        lambda: bob.http.get(f"{page_url}/versions/1").status_code,
        lambda: bob.http.post(f"{page_url}/versions/1/restore").status_code,
        lambda: (
            bob.http.post(
                "/api/items", json={"kind": "section", "title": "x", "parent_id": notebook["id"]}
            ).status_code
        ),
    ]

    assert {attempt() for attempt in attempts} == {404}
    assert bob.titles() == []
    assert bob.trashed_titles() == []
