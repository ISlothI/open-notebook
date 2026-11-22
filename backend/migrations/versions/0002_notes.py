"""Accounts, hierarchy, pages and versions.

Revision ID: 0002
Revises: 0001
"""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

UPGRADE = [
    """
    CREATE TABLE users (
        id uuid DEFAULT uuidv7() CONSTRAINT pk_users PRIMARY KEY,
        email text NOT NULL CONSTRAINT uq_users_email UNIQUE,
        password_hash text NOT NULL,
        created_at timestamptz NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE TABLE sessions (
        token_hash bytea CONSTRAINT pk_sessions PRIMARY KEY,
        user_id uuid NOT NULL CONSTRAINT fk_sessions_user_id
            REFERENCES users (id) ON DELETE CASCADE,
        expires_at timestamptz NOT NULL
    )
    """,
    "CREATE INDEX ix_sessions_user_id ON sessions (user_id)",
    """
    CREATE TABLE failed_logins (
        id uuid DEFAULT uuidv7() CONSTRAINT pk_failed_logins PRIMARY KEY,
        key bytea NOT NULL,
        at timestamptz NOT NULL
    )
    """,
    "CREATE INDEX ix_failed_logins_key_at ON failed_logins (key, at)",
    """
    CREATE TABLE nodes (
        id uuid DEFAULT uuidv7() CONSTRAINT pk_nodes PRIMARY KEY,
        owner_id uuid NOT NULL CONSTRAINT fk_nodes_owner_id
            REFERENCES users (id) ON DELETE CASCADE,
        kind text NOT NULL,
        parent_id uuid,
        parent_kind text,
        title text NOT NULL,
        position integer NOT NULL,
        created_at timestamptz NOT NULL DEFAULT now(),
        trashed_at timestamptz,
        trash_root_id uuid,
        CONSTRAINT uq_nodes_id_kind_owner_id UNIQUE (id, kind, owner_id),
        CONSTRAINT fk_nodes_parent_id_parent_kind_owner_id
            FOREIGN KEY (parent_id, parent_kind, owner_id)
            REFERENCES nodes (id, kind, owner_id) ON DELETE CASCADE,
        CONSTRAINT ck_nodes_parent_complete
            CHECK ((parent_id IS NULL) = (parent_kind IS NULL)),
        CONSTRAINT ck_nodes_placement CHECK (
            CASE kind
                WHEN 'folder' THEN parent_kind IS NULL OR parent_kind = 'folder'
                WHEN 'notebook' THEN parent_kind IS NULL OR parent_kind = 'folder'
                WHEN 'section' THEN parent_kind IS NOT NULL AND parent_kind = 'notebook'
                WHEN 'page' THEN parent_kind IS NOT NULL AND parent_kind = 'section'
                ELSE false
            END
        ),
        CONSTRAINT ck_nodes_trash_complete
            CHECK ((trashed_at IS NULL) = (trash_root_id IS NULL))
    )
    """,
    "CREATE INDEX ix_nodes_owner_id ON nodes (owner_id)",
    "CREATE INDEX ix_nodes_parent_id ON nodes (parent_id)",
    "CREATE INDEX ix_nodes_trash_root_id ON nodes (trash_root_id)",
    """
    CREATE TABLE pages (
        node_id uuid CONSTRAINT pk_pages PRIMARY KEY
            CONSTRAINT fk_pages_node_id REFERENCES nodes (id) ON DELETE CASCADE,
        current_number integer NOT NULL
    )
    """,
    """
    CREATE TABLE page_versions (
        page_id uuid NOT NULL CONSTRAINT fk_page_versions_page_id
            REFERENCES pages (node_id) ON DELETE CASCADE,
        number integer NOT NULL,
        title text NOT NULL,
        content text NOT NULL,
        created_at timestamptz NOT NULL DEFAULT now(),
        restored_from integer,
        CONSTRAINT pk_page_versions PRIMARY KEY (page_id, number)
    )
    """,
]


def upgrade() -> None:
    for statement in UPGRADE:
        op.execute(statement)


def downgrade() -> None:
    for table in ("page_versions", "pages", "nodes", "failed_logins", "sessions", "users"):
        op.execute(f"DROP TABLE {table}")
