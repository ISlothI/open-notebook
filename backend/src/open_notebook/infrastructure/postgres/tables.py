"""Table definitions; the migrations are checked against them."""

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
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

metadata = MetaData(
    naming_convention={
        "ix": "ix_%(table_name)s_%(column_0_N_name)s",
        "uq": "uq_%(table_name)s_%(column_0_N_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_N_name)s",
        "pk": "pk_%(table_name)s",
    }
)

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
