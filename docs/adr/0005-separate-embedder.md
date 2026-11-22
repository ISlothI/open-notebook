# 0005 – Separate embedder process

- **Status:** Accepted
- **Date:** 2026-11-22

## Context

Both the api (queries) and the worker (passages) need the embedding model, which takes about 230 MiB of memory (measured).

## Decision

One embedder process per environment serves both over internal HTTP. Queries wait at most one second; after a failure the api does not ask again for five seconds. Without the embedder, search uses words only and says so, and pages are indexed for words immediately while their vectors are retried.

## Alternatives

| Alternative | Why not |
|---|---|
| Model inside api and worker | With two api replicas, three copies of the model per environment |
| Only the worker has a model | Queries could not be embedded |

## Consequences

- A clear failure boundary with a defined degraded mode (flow R2).
- One network hop per search.
- The model is part of the image, so nothing is downloaded at run time; the image grows by about 125 MB.
