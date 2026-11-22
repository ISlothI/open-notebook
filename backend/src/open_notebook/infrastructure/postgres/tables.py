"""Table definitions; the migrations are checked against them."""

from typing import Any

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    FetchedValue,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    LargeBinary,
    MetaData,
    PrimaryKeyConstraint,
    Table,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.types import UserDefinedType

metadata = MetaData(
    naming_convention={
        "ix": "ix_%(table_name)s_%(column_0_N_name)s",
        "uq": "uq_%(table_name)s_%(column_0_N_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_N_name)s",
        "pk": "pk_%(table_name)s",
    }
)


class EmbeddingVector(UserDefinedType[str]):
    """pgvector's type, read and written in its text form."""

    cache_ok = True

    def __init__(self, dimensions: int) -> None:
        self.dimensions = dimensions

    def get_col_spec(self, **_options: Any) -> str:  # noqa: ANN401 - signature of SQLAlchemy
        return f"vector({self.dimensions})"


# Time-ordered identifiers keep the indexes compact.
NEW_ID = text("uuidv7()")

users = Table(
    "users",
    metadata,
    Column("id", Uuid, primary_key=True, server_default=NEW_ID),
    Column("email", Text, nullable=False, unique=True),
    Column("password_hash", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

sessions = Table(
    "sessions",
    metadata,
    Column("token_hash", LargeBinary, primary_key=True),
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("expires_at", DateTime(timezone=True), nullable=False),
)

failed_logins = Table(
    "failed_logins",
    metadata,
    Column("id", Uuid, primary_key=True, server_default=NEW_ID),
    Column("key", LargeBinary, nullable=False),
    Column("at", DateTime(timezone=True), nullable=False),
    Index(None, "key", "at"),
)

nodes = Table(
    "nodes",
    metadata,
    Column("id", Uuid, primary_key=True, server_default=NEW_ID),
    Column("owner_id", ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("kind", Text, nullable=False),
    Column("parent_id", Uuid),
    Column("parent_kind", Text),
    Column("title", Text, nullable=False),
    Column("position", Integer, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("trashed_at", DateTime(timezone=True)),
    Column("trash_root_id", Uuid),
    UniqueConstraint("id", "kind", "owner_id"),
    # The parent has the stated kind and the same owner; enforced even for faulty code.
    ForeignKeyConstraint(
        ["parent_id", "parent_kind", "owner_id"],
        ["nodes.id", "nodes.kind", "nodes.owner_id"],
        ondelete="CASCADE",
    ),
    CheckConstraint("(parent_id IS NULL) = (parent_kind IS NULL)", name="parent_complete"),
    CheckConstraint(
        "CASE kind"
        " WHEN 'folder' THEN parent_kind IS NULL OR parent_kind = 'folder'"
        " WHEN 'notebook' THEN parent_kind IS NULL OR parent_kind = 'folder'"
        " WHEN 'section' THEN parent_kind IS NOT NULL AND parent_kind = 'notebook'"
        " WHEN 'page' THEN parent_kind IS NOT NULL AND parent_kind = 'section'"
        " ELSE false END",
        name="placement",
    ),
    CheckConstraint("(trashed_at IS NULL) = (trash_root_id IS NULL)", name="trash_complete"),
    Index(None, "owner_id"),
    Index(None, "parent_id"),
    Index(None, "trash_root_id"),
)

pages = Table(
    "pages",
    metadata,
    Column("node_id", ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True),
    Column("current_number", Integer, nullable=False),
)

page_versions = Table(
    "page_versions",
    metadata,
    Column("page_id", ForeignKey("pages.node_id", ondelete="CASCADE"), nullable=False),
    Column("number", Integer, nullable=False),
    Column("title", Text, nullable=False),
    Column("content", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("restored_from", Integer),
    PrimaryKeyConstraint("page_id", "number"),
)

jobs = Table(
    "jobs",
    metadata,
    Column("id", Uuid, primary_key=True, server_default=NEW_ID),
    Column("kind", Text, nullable=False),
    Column("payload", JSONB, nullable=False),
    Column("dedupe_key", Text),
    Column("state", Text, nullable=False, server_default="queued"),
    Column("attempts", Integer, nullable=False, server_default="0"),
    Column("crashes", Integer, nullable=False, server_default="0"),
    Column("run_after", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("leased_until", DateTime(timezone=True)),
    Column("error", Text),
    Column("request_id", Text),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("finished_at", DateTime(timezone=True)),
    CheckConstraint("state IN ('queued', 'running', 'succeeded', 'dead')", name="state"),
    Index(
        "uq_jobs_waiting_dedupe_key",
        "dedupe_key",
        unique=True,
        postgresql_where=text("state = 'queued'"),
    ),
    Index(
        "ix_jobs_unfinished",
        "run_after",
        postgresql_where=text("state IN ('queued', 'running')"),
    ),
)

search_chunks = Table(
    "search_chunks",
    metadata,
    Column("page_id", ForeignKey("pages.node_id", ondelete="CASCADE"), nullable=False),
    Column("ordinal", Integer, nullable=False),
    Column("title", Text, nullable=False),
    Column("text", Text, nullable=False),
    Column("embedding", EmbeddingVector(384)),
    Column("tsv", TSVECTOR, FetchedValue(), nullable=False),
    PrimaryKeyConstraint("page_id", "ordinal"),
    Index("ix_search_chunks_tsv", "tsv", postgresql_using="gin"),
)

exports = Table(
    "exports",
    metadata,
    Column("id", Uuid, primary_key=True, server_default=NEW_ID),
    Column("owner_id", ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("item_id", ForeignKey("nodes.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("title", Text, nullable=False),
    Column("snapshot", JSONB, nullable=False),
    Column("state", Text, nullable=False, server_default="queued"),
    Column("progress", Integer, nullable=False, server_default="0"),
    Column("artifact", LargeBinary),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("finished_at", DateTime(timezone=True)),
    Column("expires_at", DateTime(timezone=True)),
    CheckConstraint(
        "state IN ('queued', 'running', 'succeeded', 'failed', 'expired')", name="state"
    ),
    CheckConstraint("(state = 'succeeded') = (artifact IS NOT NULL)", name="artifact"),
    Index(None, "owner_id", "created_at"),
)
