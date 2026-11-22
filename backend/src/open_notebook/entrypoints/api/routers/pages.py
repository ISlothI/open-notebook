from uuid import UUID

from fastapi import APIRouter, status
from prometheus_client import Counter

from open_notebook.domain.pages import VersionConflictError
from open_notebook.entrypoints.api.schemas import ErrorBody, PageBody, SavePage, VersionBody
from open_notebook.entrypoints.api.session import CurrentServices, CurrentUser

SAVES = Counter("page_saves", "Page saves", ["outcome"])

router = APIRouter(prefix="/api/pages/{page_id}", tags=["pages"])


@router.get("")
def read_page(page_id: UUID, user: CurrentUser, services: CurrentServices) -> PageBody:
    return PageBody.of(services.pages.read(user.id, page_id))


@router.put("", responses={status.HTTP_409_CONFLICT: {"model": ErrorBody}})
def save_page(
    page_id: UUID, body: SavePage, user: CurrentUser, services: CurrentServices
) -> PageBody:
    try:
        result = services.pages.save(user.id, page_id, body.title, body.content, body.base_version)
    except VersionConflictError:
        SAVES.labels("conflict").inc()
        raise
    SAVES.labels("created" if result.created else "unchanged").inc()
    return PageBody.of(result.version)


@router.get("/versions")
def list_versions(page_id: UUID, user: CurrentUser, services: CurrentServices) -> list[VersionBody]:
    return [VersionBody.of(item) for item in services.pages.list_versions(user.id, page_id)]


@router.get("/versions/{number}")
def read_version(
    page_id: UUID, number: int, user: CurrentUser, services: CurrentServices
) -> PageBody:
    return PageBody.of(services.pages.read_version(user.id, page_id, number))


@router.post("/versions/{number}/restore")
def restore_version(
    page_id: UUID, number: int, user: CurrentUser, services: CurrentServices
) -> PageBody:
    return PageBody.of(services.pages.restore_version(user.id, page_id, number).version)
