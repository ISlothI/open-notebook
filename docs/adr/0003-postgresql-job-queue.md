# 0003 – Job queue in PostgreSQL

- **Status:** Accepted
- **Date:** 2026-11-22

## Context

Saving a page must lead to indexing, and an export request to a PDF, even if a process crashes in between. The volume is small (one job per save). The memory budget is tight.

## Decision

Jobs are rows in PostgreSQL, written in the same transaction as the change that causes them. Workers claim them with `FOR UPDATE SKIP LOCKED`, hold a renewed lease, and are woken by `LISTEN/NOTIFY` with polling as fallback. The attempt number fences off a worker that lost its lease. Failures back off exponentially; a job is buried after three failures or three crashes of its worker, while an outage of a dependency postpones it without limit. Each kind has its own worker thread, so that a flood of indexing does not delay exports (a live exercise had shown a delay of 31 seconds).

## Alternatives

| Alternative | Why not |
|---|---|
| Redis or RabbitMQ | A second stateful system; the save and its job would not be atomic without an outbox anyway |
| A queue library (e.g. Procrastinate) | Good quality, but the export status shown to users and the merging of indexing jobs need our own model on top |
| Indexing inside the request | Saving would be as slow and as unreliable as the embedder |

## Consequences

- Execution is at least once, so every handler is idempotent.
- Waiting jobs with the same key are merged. The merge *updates* the waiting row, which keeps workers from starting it before the merging transaction commits; otherwise the last save could be missed.
- A retried job loses its merge key, because a newer job with the same key may already be waiting.
- Throughput is limited by the database, far above the needs of this system.
