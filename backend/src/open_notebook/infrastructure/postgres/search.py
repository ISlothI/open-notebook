"""Hybrid search: full-text and vector rankings merged by reciprocal rank fusion."""

from uuid import UUID

from sqlalchemy import Connection, RowMapping, delete, insert, text

from open_notebook.domain.search import Chunk, SearchHit, SnippetPart, Vector
from open_notebook.infrastructure.postgres.tables import search_chunks

# The constant of the original RRF paper; it dampens the advantage of the first ranks.
RRF_K = 60
CANDIDATES = 50
# Related passages of the search quality set are nearer, unrelated ones are farther.
MAX_VECTOR_DISTANCE = 0.70
MATCH_START, MATCH_END = "\x02", "\x03"
SNIPPET_LENGTH = 220

FIND = text("""
    WITH query AS (
        SELECT websearch_to_tsquery('hungarian', :query)
            || websearch_to_tsquery('english', :query)
            || websearch_to_tsquery('on_plain', :query) AS terms
    ),
    visible AS (
        SELECT page.id AS page_id, page.title, section.title AS section_title,
               notebook.id AS notebook_id, notebook.title AS notebook_title
        FROM nodes page
        JOIN nodes section ON section.id = page.parent_id
        JOIN nodes notebook ON notebook.id = section.parent_id
        WHERE page.owner_id = :owner_id AND page.kind = 'page' AND page.trashed_at IS NULL
          AND (CAST(:notebook_id AS uuid) IS NULL OR notebook.id = :notebook_id)
    ),
    text_matches AS (
        SELECT DISTINCT ON (page_id) page_id, ordinal, score
        FROM (
            SELECT chunk.page_id, chunk.ordinal, ts_rank_cd(chunk.tsv, query.terms) AS score
            FROM search_chunks chunk JOIN visible USING (page_id), query
            WHERE chunk.tsv @@ query.terms
        ) matching
        ORDER BY page_id, score DESC, ordinal
    ),
    vector_matches AS (
        SELECT DISTINCT ON (page_id) page_id, ordinal, distance
        FROM (
            SELECT chunk.page_id, chunk.ordinal,
                   chunk.embedding <=> CAST(:vector AS vector) AS distance
            FROM search_chunks chunk JOIN visible USING (page_id)
            WHERE CAST(:vector AS vector) IS NOT NULL AND chunk.embedding IS NOT NULL
        ) near
        WHERE distance <= :max_distance
        ORDER BY page_id, distance, ordinal
    ),
    ranked AS (
        (SELECT page_id, ordinal, 0 AS source,
                row_number() OVER (ORDER BY score DESC, page_id) AS rank
         FROM text_matches ORDER BY rank LIMIT :candidates)
        UNION ALL
        (SELECT page_id, ordinal, 1 AS source,
                row_number() OVER (ORDER BY distance, page_id) AS rank
         FROM vector_matches ORDER BY rank LIMIT :candidates)
    ),
    fused AS (
        SELECT page_id, sum(1.0 / (:rrf_k + rank)) AS score,
               -- The text match is preferred for the snippet, because it can be highlighted.
               (array_agg(ordinal ORDER BY source))[1] AS ordinal
        FROM ranked GROUP BY page_id
        ORDER BY score DESC, page_id LIMIT :limit
    )
    SELECT visible.*, left(chunk.text, :snippet_length) AS beginning,
           ts_headline('hungarian', chunk.text, query.terms, :headline_options) AS headline
    FROM fused
    JOIN visible USING (page_id)
    JOIN search_chunks chunk USING (page_id, ordinal), query
    ORDER BY fused.score DESC, page_id
""")

HEADLINE_OPTIONS = f"StartSel={MATCH_START}, StopSel={MATCH_END}, MaxWords=32, MinWords=16"


def to_literal(vector: Vector) -> str:
    return "[" + ",".join(f"{value:.6f}" for value in vector) + "]"


def to_snippet(row: RowMapping) -> list[SnippetPart]:
    headline: str = row["headline"]
    if MATCH_START not in headline:
        return [SnippetPart(row["beginning"], is_match=False)] if row["beginning"] else []
    before, *matches = headline.split(MATCH_START)
    parts = [SnippetPart(before, is_match=False)]
    for match in matches:
        matched, _, after = match.partition(MATCH_END)
        parts += [SnippetPart(matched, is_match=True), SnippetPart(after, is_match=False)]
    return [part for part in parts if part.text]


class PostgresSearchIndex:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def replace_chunks(
        self, page_id: UUID, chunks: list[Chunk], vectors: list[Vector] | None
    ) -> None:
        self._connection.execute(delete(search_chunks).where(search_chunks.c.page_id == page_id))
        self._connection.execute(
            insert(search_chunks),
            [
                {
                    "page_id": page_id,
                    "ordinal": ordinal,
                    "title": chunk.title,
                    "text": chunk.text,
                    "embedding": to_literal(vectors[ordinal]) if vectors else None,
                }
                for ordinal, chunk in enumerate(chunks)
            ],
        )

    def find(
        self,
        owner_id: UUID,
        query: str,
        vector: Vector | None,
        notebook_id: UUID | None,
        limit: int,
    ) -> list[SearchHit]:
        rows = self._connection.execute(
            FIND,
            {
                "owner_id": owner_id,
                "query": query,
                "vector": to_literal(vector) if vector else None,
                "notebook_id": notebook_id,
                "limit": limit,
                "candidates": CANDIDATES,
                "max_distance": MAX_VECTOR_DISTANCE,
                "rrf_k": RRF_K,
                "snippet_length": SNIPPET_LENGTH,
                "headline_options": HEADLINE_OPTIONS,
            },
        ).mappings()
        return [
            SearchHit(
                page_id=row["page_id"],
                title=row["title"],
                section_title=row["section_title"],
                notebook_id=row["notebook_id"],
                notebook_title=row["notebook_title"],
                snippet=to_snippet(row),
            )
            for row in rows
        ]
