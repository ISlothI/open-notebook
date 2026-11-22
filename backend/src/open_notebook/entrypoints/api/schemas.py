"""Request and response bodies."""

from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, Field

from open_notebook.domain.accounts import User
from open_notebook.domain.library import Node, NodeKind
from open_notebook.domain.pages import PageVersion, VersionSummary
from open_notebook.domain.search import SearchMode, SearchResults


class Credentials(BaseModel):
    email: str
    password: str = Field(max_length=1024)


class UserBody(BaseModel):
    id: UUID
    email: str

    @classmethod
    def of(cls, user: User) -> Self:
        return cls(id=user.id, email=user.email)


class NodeBody(BaseModel):
    id: UUID
    kind: NodeKind
    parent_id: UUID | None
    title: str
    position: int
    created_at: datetime
    trashed_at: datetime | None

    @classmethod
    def of(cls, node: Node) -> Self:
        return cls(
            id=node.id,
            kind=node.kind,
            parent_id=node.parent_id,
            title=node.title,
            position=node.position,
            created_at=node.created_at,
            trashed_at=node.trashed_at,
        )


class CreateNode(BaseModel):
    kind: NodeKind
    parent_id: UUID | None = None
    title: str


class RenameNode(BaseModel):
    title: str


class MoveNode(BaseModel):
    parent_id: UUID | None
    position: int = Field(ge=0)


class RestoreNode(BaseModel):
    parent_id: UUID | None = None


class PageBody(BaseModel):
    id: UUID
    version: int
    title: str
    content: str
    saved_at: datetime
    restored_from: int | None

    @classmethod
    def of(cls, version: PageVersion) -> Self:
        return cls(
            id=version.page_id,
            version=version.number,
            title=version.title,
            content=version.content,
            saved_at=version.created_at,
            restored_from=version.restored_from,
        )


class SavePage(BaseModel):
    title: str
    content: str
    base_version: int


class VersionBody(BaseModel):
    version: int
    title: str
    saved_at: datetime
    restored_from: int | None

    @classmethod
    def of(cls, summary: VersionSummary) -> Self:
        return cls(
            version=summary.number,
            title=summary.title,
            saved_at=summary.created_at,
            restored_from=summary.restored_from,
        )


class ErrorBody(BaseModel):
    code: str
    message: str
    current: PageBody | None = None


class SnippetPartBody(BaseModel):
    text: str
    is_match: bool


class SearchHitBody(BaseModel):
    page_id: UUID
    title: str
    section_title: str
    notebook_id: UUID
    notebook_title: str
    snippet: list[SnippetPartBody]


class SearchBody(BaseModel):
    mode: SearchMode
    hits: list[SearchHitBody]

    @classmethod
    def of(cls, results: SearchResults) -> Self:
        return cls.model_validate(results, from_attributes=True)
