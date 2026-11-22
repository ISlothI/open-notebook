# Phase 1 – Walking skeleton and CI

- **Date:** 2026-11-22
- **Commit:** `0154805`
- **Environment:** local: macOS on arm64, Docker 29.4.3; CI: GitHub-hosted `ubuntu-24.04` (amd64)

## 1. The stack is healthy from one command

`make dev` and `make up` both finished with every service healthy. `make smoke` against each of them:

```text
3 passed in 0.17s        # make dev
3 passed in 0.20s        # make up
```

The smoke test checks readiness down to the database, the served web application, and that metrics are not public, through the proxy with a verified certificate. Changing a source file was visible in the running development api without a restart by hand.

## 2. CI is green, and red on a deliberate error

| Run | Change | Result |
|---|---|---|
| [45056484081](https://github.com/ISlothI/open-notebook/actions/runs/45056484081) | phase 1 (PR #4) | all three jobs passed |
| [45056619259](https://github.com/ISlothI/open-notebook/actions/runs/45056619259) | readiness always answers 200 (PR #5, closed without merging) | failed |

```text
E       assert 200 == 503
FAILED tests/unit/test_api.py::test_not_ready_when_database_is_down
1 failed, 14 passed in 0.39s
```

The first run also proves that `make check` works on amd64 Linux, which phase 0 left open.

## 3. Database outage and shutdown (production images, local)

```text
database stopped:   live 200   ready 503 (0.058 s)
database restarted: ready 200
stopping worker and api: 0.6 s, last worker log event "worker_stopped"
```

## 4. Measured idle memory (MiB, production images)

| db | api | worker | web | proxy |
|---:|---:|---:|---:|---:|
| 33 | 73 | 58 | 52 | 17 |

One sample right after start, without load.

## Interpretation

The "Done when" condition is met. The smoke and integration tests did not notice the deliberate error because they do not stop the database; the unit test is what covers this behaviour.
