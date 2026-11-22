# 0004 – Hybrid search in PostgreSQL

- **Status:** Accepted
- **Date:** 2026-11-22

## Context

Notes in Hungarian and English must be found by words and by meaning, limited to their owner, without trashed pages. The number of chunks per user is in the thousands.

## Decision

Full-text search (Hungarian and English stemming plus an accent-insensitive form) and vector search (pgvector, cosine) run in one SQL statement; reciprocal rank fusion merges the rankings. Vector search is exact, and distant matches are dropped. Visibility is decided by joining the hierarchy at query time, so trashing and moving need no reindexing.

## Choice of the embedding model

Both candidates were measured on the fixed bilingual sample in `test_search_quality.py` (20 pages, 23 queries), vector ranking only:

| Model (quantised, about 118 MB) | recall@5 | MRR | Nearest unrelated match |
|---|---:|---:|---|
| multilingual-e5-small | 0.91 | 0.70 | as near as related ones |
| **paraphrase-multilingual-MiniLM-L12-v2** (Apache-2.0) | **0.96** | **0.94** | clearly farther |

The planned model, e5-small, failed the thresholds set beforehand (with fusion and distance limit: recall@5 0.74, MRR 0.63), mainly on queries in the other language. The thresholds were kept and the model was replaced. The complete search reaches recall@5 0.91 and MRR 0.91.

The SentencePiece tokenizer replaces the `tokenizers` library: identical tokens on 52 of 53 compared texts (the exception is 500 repetitions of one letter) and about 220 MiB less memory.

## Alternatives

| Alternative | Why not |
|---|---|
| Elasticsearch, OpenSearch | More memory than the whole budget; dual writes |
| Separate vector database | Dual writes; ownership and trash filters would be duplicated |
| Embedding API of a provider | Paid, and private notes would leave the system |

## Consequences

- Index and data are consistent and backed up together.
- The distance limit was chosen on the same small sample that measures it, so the real quality may differ.
- An approximate index (HNSW) is added only if load measurement requires it.
