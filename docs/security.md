# Security notes

## Secret inventory

| Secret | Where it is created | Where it is stored | Rotation |
|---|---|---|---|
| Local database password | `make env` (random) | gitignored `.env`, mode 600 | delete `.env` and the project's `db-data` volume |

Every new secret is recorded here in the change that introduces it.

## Controls in place

| Control | Implementation | Verified by |
|---|---|---|
| Secrets do not enter Git | gitleaks on the full history, staged and unstaged changes; also in the pre-commit hook | `make test-gates` |
| Tools are authentic | SHA-256 verified downloads, base image pinned by digest | [phase 0 evidence](evidence/phase-00-foundation.md) |
| Checks have minimal rights | no network, no capabilities, no new privileges, calling user's ID, no Docker socket | `Makefile` |

| Containers have minimal rights | non-root, read-only root filesystem, no capabilities (api, worker, web) | `compose/compose.yaml` |
| The database is not reachable from outside | internal network, no published port | `compose/compose.yaml` |
| Metrics are not public | the proxy routes only `/api` to the api | smoke test |

## Known limitations

- Git hooks are optional per clone and can be bypassed; the same gates run in CI.
- gitleaks finds known patterns and high-entropy strings; it does not prove that no secret exists.
- Files that git does not track are scanned only when staged.
