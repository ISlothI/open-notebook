# 0007 – Export files in PostgreSQL

- **Status:** Accepted
- **Date:** 2026-11-22

## Context

A worker produces a file that the api serves later. Files are small (limited to 25 MB), can be reproduced, and are needed only for a short time.

## Decision

Files are stored in the `exports` table behind the `ArtifactStore` port, expire after 24 hours and are removed by the cleanup. The download link is protected by the session and ownership.

The originally planned signed link was dropped: the session already protects the download, and a signing key would be one more secret.

## Alternatives

| Alternative | Why not |
|---|---|
| Object storage (S3-compatible) | A separate stateful system for short-lived small files; the port makes a later change local |
| Shared volume | Needs a volume writable by two workloads, which ties them to one node |

## Consequences

- Finishing an export and storing its file is one transaction, so a status never points to a missing file.
- Backups include unexpired files.
- The link works only for the signed-in owner.
