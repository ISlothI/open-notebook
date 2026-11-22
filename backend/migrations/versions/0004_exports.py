"""PDF exports and crash accounting of jobs.

Revision ID: 0004
Revises: 0003
"""

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE jobs ADD COLUMN crashes integer NOT NULL DEFAULT 0")
    op.execute("""
        CREATE TABLE exports (
            id uuid DEFAULT uuidv7() CONSTRAINT pk_exports PRIMARY KEY,
            owner_id uuid NOT NULL CONSTRAINT fk_exports_owner_id
                REFERENCES users (id) ON DELETE CASCADE,
            item_id uuid NOT NULL CONSTRAINT fk_exports_item_id
                REFERENCES nodes (id) ON DELETE CASCADE,
            title text NOT NULL,
            snapshot jsonb NOT NULL,
            state text NOT NULL DEFAULT 'queued',
            progress integer NOT NULL DEFAULT 0,
            artifact bytea,
            created_at timestamptz NOT NULL DEFAULT now(),
            finished_at timestamptz,
            expires_at timestamptz,
            CONSTRAINT ck_exports_state CHECK (
                state IN ('queued', 'running', 'succeeded', 'failed', 'expired')
            ),
            CONSTRAINT ck_exports_artifact CHECK ((state = 'succeeded') = (artifact IS NOT NULL))
        )
    """)
    op.execute("CREATE INDEX ix_exports_item_id ON exports (item_id)")
    op.execute("CREATE INDEX ix_exports_owner_id_created_at ON exports (owner_id, created_at)")


def downgrade() -> None:
    op.execute("DROP TABLE exports")
    op.execute("ALTER TABLE jobs DROP COLUMN crashes")
