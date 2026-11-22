from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query
from prometheus_client import Counter

from open_notebook.entrypoints.api.schemas import SearchBody
from open_notebook.entrypoints.api.session import CurrentServices, CurrentUser

SEARCHES = Counter("searches", "Searches", ["mode"])

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("")
def search(
    q: Annotated[str, Query(max_length=1_000)],
    user: CurrentUser,
    services: CurrentServices,
    notebook_id: UUID | None = None,
) -> SearchBody:
    results = services.search.search(user.id, q, notebook_id)
    SEARCHES.labels(results.mode).inc()
    return SearchBody.of(results)
