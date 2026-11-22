# Security notes

## Secret inventory

| Secret | Where it is created | Where it is stored | Rotation |
|---|---|---|---|
| – | – | – | – |

No secret exists yet. Every new secret is recorded here in the change that introduces it.

## Controls in place

| Control | Implementation | Verified by |
|---|---|---|
| Secrets do not enter Git | gitleaks on the full history, staged and unstaged changes; also in the pre-commit hook | `make test-gates` |
| Tools are authentic | SHA-256 verified downloads, base image pinned by digest | [phase 0 evidence](evidence/phase-00-foundation.md) |
| Checks have minimal rights | no network, no capabilities, no new privileges, calling user's ID, no Docker socket | `Makefile` |

## Known limitations

- Git hooks are optional per clone and can be bypassed; the same gates run in CI from phase 1.
- gitleaks finds known patterns and high-entropy strings; it does not prove that no secret exists.
- Files that git does not track are scanned only when staged.
