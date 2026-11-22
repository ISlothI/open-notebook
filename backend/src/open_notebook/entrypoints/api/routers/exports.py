from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Response, status

from open_notebook.entrypoints.api.schemas import ExportBody, RequestExport
from open_notebook.entrypoints.api.session import CurrentServices, CurrentUser

router = APIRouter(prefix="/api/exports", tags=["exports"])


@router.post("", status_code=status.HTTP_202_ACCEPTED)
def request_export(body: RequestExport, user: CurrentUser, services: CurrentServices) -> ExportBody:
    return ExportBody.of(services.exports.request(user.id, body.item_id))


@router.get("")
def list_exports(user: CurrentUser, services: CurrentServices) -> list[ExportBody]:
    return [ExportBody.of(export) for export in services.exports.list_exports(user.id)]


@router.get("/{export_id}")
def read_export(export_id: UUID, user: CurrentUser, services: CurrentServices) -> ExportBody:
    return ExportBody.of(services.exports.read(user.id, export_id))


@router.get("/{export_id}/download", response_class=Response)
def download_export(export_id: UUID, user: CurrentUser, services: CurrentServices) -> Response:
    export, artifact = services.exports.download(user.id, export_id)
    file_name = quote(f"{export.title}.pdf", safe="")
    return Response(
        artifact,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{file_name}",
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )
