# 0002 – One backend codebase and image, several processes

- **Status:** Accepted
- **Date:** 2026-11-22

## Context

The api answers interactive requests, the worker does slow background work, and the embedder will hold a model in memory. They share the domain code and the database schema. One person builds and operates them within a memory budget of about 3.8 GiB.

## Decision

One Python package and one image contain every process; the command selects which one runs. The database schema is migrated by the same image. The web application is a separate static image.

## Alternatives

| Alternative | Why not |
|---|---|
| One process | A long export would compete with requests and fail together with them |
| One image per process | Triple building, scanning, SBOMs and signing without independent release cadence |
| Microservices with separate databases | Distributed transactions would be needed for "save and index" |

## Consequences

- The processes of a release always match each other.
- Processes scale, fail and get resource limits separately.
- Each image carries some dependencies that a given process does not load: larger on disk, but not in memory.
