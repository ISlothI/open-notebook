"""Guards the relevance of search with the real model on a fixed bilingual sample."""

from collections.abc import Iterator
from statistics import mean

import pytest
from sqlalchemy import Engine

from open_notebook.domain.search import Vector
from open_notebook.infrastructure.onnx_embedder import OnnxEmbedder
from tests.integration.conftest import build_job_runner, build_test_client, empty_database
from tests.integration.notebook_client import NotebookClient

MIN_RECALL_AT_5 = 0.9
MIN_MRR = 0.75
MIN_REFUSED_UNRELATED = 0.5

DOCUMENTS = {
    "Sourdough": "Feed the starter twice a day. Knead the dough, let it rest overnight and bake it.",
    "Kovászos kenyér": "A kovászt naponta kétszer etetjük. A tésztát éjszakára pihentetjük.",
    "Kubernetes basics": "A Deployment keeps the desired number of Pods running and replaces failed ones.",
    "Docker": "An image is built from layers. A container is a running instance of an image.",
    "Adatbázis-mentés": "A mentést óránként készítjük, és negyedévente gyakoroljuk a visszaállítást.",
    "TLS": "A certificate binds a public key to a host name and is signed by an authority.",
    "Photosynthesis": "Plants turn light, water and carbon dioxide into sugar and oxygen.",
    "Magyar történelem": "A honfoglalás után a magyarok a Kárpát-medencében telepedtek le.",
    "Budapest trip": "Walk across the Chain Bridge, visit the thermal baths and the castle.",
    "Marathon training": "Increase the weekly distance slowly and rest after long runs.",
    "Edzésterv": "Hetente három erősítő edzés, közte pihenőnapokkal és nyújtással.",
    "Household budget": "Rent and food take half of the income; put a tenth aside every month.",
    "Lakáshitel": "A törlesztőrészlet a kamattól és a futamidőtől függ.",
    "Meeting notes": "Anna prepares the slides, Peter calls the client before Friday.",
    "Childhood vaccines": "The doctor recommends the next injection at fifteen months of age.",
    "Gyógyszerek": "A vérnyomáscsökkentőt reggel, étkezés előtt kell bevenni.",
    "Guitar chords": "Practise the change between G, C and D until it is smooth.",
    "Garden in spring": "Sow tomatoes indoors in March and move the seedlings out in May.",
    "Macska": "A cica naponta kétszer eszik, és oltásra kell vinni az állatorvoshoz.",
    "Tax return": "Collect the invoices and send the declaration to the authority by May.",
}

# A query in other words, often in the other language, and the page it should find.
QUERIES = {
    "how to bake bread": {"Sourdough", "Kovászos kenyér"},
    "kenyérsütés": {"Sourdough", "Kovászos kenyér"},
    "container orchestration": {"Kubernetes basics", "Docker"},
    "konténer létrehozása képfájlból": {"Docker"},
    "disaster recovery of data": {"Adatbázis-mentés"},
    "visszaállítás": {"Adatbázis-mentés"},
    "secure connection to a website": {"TLS"},
    "biztonságos webes kapcsolat tanúsítvánnyal": {"TLS"},
    "how do leaves make energy": {"Photosynthesis"},
    "settlement of the Hungarians": {"Magyar történelem"},
    "city sightseeing": {"Budapest trip"},
    "városnézés hidakkal és fürdőkkel": {"Budapest trip"},
    "preparing for a long distance race": {"Marathon training"},
    "gym workout": {"Edzésterv"},
    "saving money": {"Household budget"},
    "mortgage payments": {"Lakáshitel"},
    "who has to phone the customer": {"Meeting notes"},
    "immunisation of children": {"Childhood vaccines"},
    "blood pressure pills": {"Gyógyszerek"},
    "learning a musical instrument": {"Guitar chords"},
    "paradicsom ültetése": {"Garden in spring"},
    "feeding the cat": {"Macska"},
    "adóbevallás": {"Tax return"},
}

UNRELATED = ["quantum chromodynamics", "zzzz qqqq", "submarine sonar repair", "opera libretto 1786"]


class LocalModel:
    def __init__(self) -> None:
        self._model = OnnxEmbedder(threads=2)

    def embed_query(self, query: str) -> Vector:
        return self._model.embed([query])[0]

    def embed_passages(self, passages: list[str]) -> list[Vector]:
        return self._model.embed(passages)


@pytest.fixture(scope="module")
def library(engine: Engine) -> Iterator[NotebookClient]:
    empty_database(engine)
    model = LocalModel()
    client = build_test_client(engine, model)
    client.register("quality@example.test")
    section = client.create("section", "S", client.create("notebook", "N"))
    for title, content in DOCUMENTS.items():
        client.save(client.create("page", title, section), title, content, base=1)
    build_job_runner(engine, model)()
    yield client


def test_relevant_pages_come_first(library: NotebookClient) -> None:
    ranks: dict[str, int | None] = {}
    for query, expected in QUERIES.items():
        found = library.found_titles(query)
        ranks[query] = next((i for i, title in enumerate(found, 1) if title in expected), None)

    recall = mean(rank is not None and rank <= 5 for rank in ranks.values())
    reciprocal_rank = mean(1 / rank if rank else 0 for rank in ranks.values())
    not_first = {query: rank for query, rank in ranks.items() if rank != 1}
    print(f"recall@5={recall:.2f} MRR={reciprocal_rank:.2f} not first={not_first}")

    assert recall >= MIN_RECALL_AT_5
    assert reciprocal_rank >= MIN_MRR


def test_unrelated_queries_find_little(library: NotebookClient) -> None:
    counts = {query: len(library.found_titles(query)) for query in UNRELATED}
    print(f"unrelated: {counts}")

    assert mean(count <= 3 for count in counts.values()) >= MIN_REFUSED_UNRELATED
