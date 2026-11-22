"""Job queue and search index.

Revision ID: 0003
Revises: 0002
"""

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def weighted(configuration: str) -> str:
    return (
        f"setweight(to_tsvector('{configuration}', title), 'A') || "
        f"to_tsvector('{configuration}', text)"
    )


def upgrade() -> None:
    op.execute("""
        CREATE TABLE jobs (
            id uuid DEFAULT uuidv7() CONSTRAINT pk_jobs PRIMARY KEY,
            kind text NOT NULL,
            payload jsonb NOT NULL,
            dedupe_key text,
            state text NOT NULL DEFAULT 'queued',
            attempts integer NOT NULL DEFAULT 0,
            run_after timestamptz NOT NULL DEFAULT now(),
            leased_until timestamptz,
            error text,
            request_id text,
            created_at timestamptz NOT NULL DEFAULT now(),
            finished_at timestamptz,
            CONSTRAINT ck_jobs_state CHECK (state IN ('queued', 'running', 'succeeded', 'dead'))
        )
    """)
    # At most one waiting job per key; a running one does not block the next.
    op.execute("""
        CREATE UNIQUE INDEX uq_jobs_waiting_dedupe_key ON jobs (dedupe_key)
        WHERE state = 'queued'
    """)
    op.execute("""
        CREATE INDEX ix_jobs_unfinished ON jobs (run_after)
        WHERE state IN ('queued', 'running')
    """)
    # Hungarian and English stemming need accents; the third form ignores them.
    op.execute("CREATE TEXT SEARCH CONFIGURATION on_plain (COPY = simple)")
    op.execute("""
        ALTER TEXT SEARCH CONFIGURATION on_plain
        ALTER MAPPING FOR hword, hword_part, word WITH unaccent, simple
    """)
    op.execute(f"""
        CREATE TABLE search_chunks (
            page_id uuid NOT NULL CONSTRAINT fk_search_chunks_page_id
                REFERENCES pages (node_id) ON DELETE CASCADE,
            ordinal integer NOT NULL,
            title text NOT NULL,
            text text NOT NULL,
            embedding vector(384),
            tsv tsvector NOT NULL GENERATED ALWAYS AS (
                {weighted("hungarian")} || {weighted("english")} || {weighted("on_plain")}
            ) STORED,
            CONSTRAINT pk_search_chunks PRIMARY KEY (page_id, ordinal)
        )
    """)
    op.execute("CREATE INDEX ix_search_chunks_tsv ON search_chunks USING gin (tsv)")
    # Pages created before this migration become searchable as well.
    op.execute("""
        INSERT INTO jobs (kind, payload, dedupe_key)
        SELECT 'index_page', jsonb_build_object('page_id', node_id), 'index_page:' || node_id
        FROM pages
    """)


def downgrade() -> None:
    op.execute("DROP TABLE search_chunks")
    op.execute("DROP TEXT SEARCH CONFIGURATION on_plain")
    op.execute("DROP TABLE jobs")
