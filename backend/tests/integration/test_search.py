from collections.abc import Callable

from sqlalchemy import Engine, text

from tests.fakes import FakeEmbeddings
from tests.integration.notebook_client import Json, NotebookClient

type RunJobs = Callable[[], int]


def add_page(client: NotebookClient, title: str, content: str, notebook: str = "Notebook") -> Json:
    """Returns the notebook of the new page."""
    parent = client.create("notebook", notebook)
    page = client.create("page", title, client.create("section", "Section", parent))
    client.save(page, title, content, base=1)
    return parent


def test_saved_page_is_found_by_its_words(alice: NotebookClient, run_jobs: RunJobs) -> None:
    add_page(alice, "Recipes", "Knead the dough slowly.")
    assert alice.found_titles("dough") == []

    run_jobs()

    result = alice.search("dough")
    assert result["mode"] == "hybrid"
    hit = result["hits"][0]
    assert (hit["title"], hit["section_title"], hit["notebook_title"]) == (
        "Recipes",
        "Section",
        "Notebook",
    )
    assert {"text": "dough", "is_match": True} in hit["snippet"]


def test_page_is_found_by_meaning(alice: NotebookClient, run_jobs: RunJobs) -> None:
    add_page(alice, "Trip", "The automobile was fast.")
    add_page(alice, "Health", "The physician was kind.")
    run_jobs()

    assert alice.found_titles("car") == ["Trip"]


def test_hungarian_words_are_stemmed_and_accents_are_optional(
    alice: NotebookClient, run_jobs: RunJobs
) -> None:
    add_page(alice, "Kert", "A kertekben virágok nyílnak, és tükörfúrógép zúg.")
    run_jobs()

    for query in ("kert", "virág", "tükörfúrógép", "tukorfurogep"):
        assert alice.found_titles(query) == ["Kert"], query


def test_title_is_searchable_and_outranks_text(alice: NotebookClient, run_jobs: RunJobs) -> None:
    add_page(alice, "Other", "kubernetes is mentioned here")
    add_page(alice, "Kubernetes", "something else")
    run_jobs()

    assert alice.found_titles("kubernetes") == ["Kubernetes", "Other"]


def test_search_can_be_limited_to_a_notebook(alice: NotebookClient, run_jobs: RunJobs) -> None:
    first = add_page(alice, "First", "shared word", "One")
    add_page(alice, "Second", "shared word", "Two")
    run_jobs()

    assert set(alice.found_titles("shared")) == {"First", "Second"}
    assert alice.found_titles("shared", first) == ["First"]


def test_edit_replaces_what_is_found(alice: NotebookClient, run_jobs: RunJobs) -> None:
    page = alice.create_page("Page")
    alice.save(page, "Page", "obsolete", base=1)
    run_jobs()
    alice.save(page, "Page", "replacement", base=2)
    run_jobs()

    assert alice.found_titles("obsolete") == []
    assert alice.found_titles("replacement") == ["Page"]


def test_quick_saves_are_indexed_once(alice: NotebookClient, run_jobs: RunJobs) -> None:
    page = alice.create_page("Page")
    for base in range(1, 6):
        alice.save(page, "Page", f"text {base}", base)

    assert run_jobs() == 1


def test_f4_trashed_page_is_not_found_until_restored(
    alice: NotebookClient, run_jobs: RunJobs
) -> None:
    notebook = add_page(alice, "Page", "precious")
    run_jobs()

    alice.trash(notebook)
    assert alice.found_titles("precious") == []

    alice.restore(notebook)
    assert alice.found_titles("precious") == ["Page"]


def test_other_users_notes_are_never_found(
    alice: NotebookClient, bob: NotebookClient, run_jobs: RunJobs
) -> None:
    notebook = add_page(alice, "Secret car", "the automobile")
    run_jobs()

    assert bob.found_titles("car") == []
    assert bob.found_titles("secret") == []
    assert bob.found_titles("secret", notebook) == []


def test_r2_search_works_without_the_embedder_and_catches_up(
    alice: NotebookClient, run_jobs: RunJobs, embeddings: FakeEmbeddings, engine: Engine
) -> None:
    embeddings.available = False
    add_page(alice, "Trip", "The automobile was fast.")
    run_jobs()

    degraded = alice.search("automobile")
    assert degraded["mode"] == "fulltext"
    assert [hit["title"] for hit in degraded["hits"]] == ["Trip"]
    assert alice.found_titles("car") == []

    embeddings.available = True
    with engine.begin() as connection:
        connection.execute(text("UPDATE jobs SET leased_until = now() - interval '1 s'"))
    run_jobs()

    assert alice.search("car")["mode"] == "hybrid"
    assert alice.found_titles("car") == ["Trip"]


def test_job_of_a_purged_page_succeeds(
    alice: NotebookClient, run_jobs: RunJobs, engine: Engine
) -> None:
    alice.create_page()
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM nodes"))

    assert run_jobs() == 1
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT state FROM jobs")) == "succeeded"


def test_job_remembers_the_request_that_caused_it(alice: NotebookClient, engine: Engine) -> None:
    page = alice.create_page()
    response = alice.try_save(page, "Page", "text", 1)

    with engine.connect() as connection:
        request_id = connection.scalar(text("SELECT request_id FROM jobs"))
    assert request_id == response.headers["X-Request-ID"]


def test_strange_queries_are_harmless(alice: NotebookClient) -> None:
    for query in ("'", '"', "a:*", "& | !", "\\", "<script>", "-", "or"):
        assert alice.search(query)["hits"] == []
    assert alice.http.get("/api/search", params={"q": " "}).status_code == 422
