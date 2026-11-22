from uuid import UUID

from fastapi import APIRouter, status

from open_notebook.entrypoints.api.schemas import (
    CreateNode,
    MoveNode,
    NodeBody,
    RenameNode,
    RestoreNode,
)
from open_notebook.entrypoints.api.session import CurrentServices, CurrentUser

router = APIRouter(prefix="/api", tags=["library"])


@router.get("/items")
def list_items(user: CurrentUser, services: CurrentServices) -> list[NodeBody]:
    return [NodeBody.of(node) for node in services.library.list_items(user.id)]


@router.post("/items", status_code=status.HTTP_201_CREATED)
def create_item(body: CreateNode, user: CurrentUser, services: CurrentServices) -> NodeBody:
    return NodeBody.of(services.library.create(user.id, body.kind, body.parent_id, body.title))


@router.patch("/items/{item_id}")
def rename_item(
    item_id: UUID, body: RenameNode, user: CurrentUser, services: CurrentServices
) -> NodeBody:
    return NodeBody.of(services.library.rename(user.id, item_id, body.title))


@router.post("/items/{item_id}/move")
def move_item(
    item_id: UUID, body: MoveNode, user: CurrentUser, services: CurrentServices
) -> NodeBody:
    return NodeBody.of(services.library.move(user.id, item_id, body.parent_id, body.position))


@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def trash_item(item_id: UUID, user: CurrentUser, services: CurrentServices) -> None:
    services.library.trash(user.id, item_id)


@router.get("/trash")
def list_trash(user: CurrentUser, services: CurrentServices) -> list[NodeBody]:
    return [NodeBody.of(node) for node in services.library.list_trash(user.id)]


@router.post("/trash/{item_id}/restore")
def restore_item(
    item_id: UUID, body: RestoreNode, user: CurrentUser, services: CurrentServices
) -> NodeBody:
    return NodeBody.of(services.library.restore(user.id, item_id, body.parent_id))
