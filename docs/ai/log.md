# AI usage log

Assistant: Claude Code (Claude Opus 5.5). Human reviews are recorded only if they took place.

## 2026-11-22 – Planning

| | |
|---|---|
| Task | Working guide and project plan from the assignment |
| AI proposal | Architecture, 12 phases, decisions; minimal sign-in raised as an addition to the specification |
| Human decision | Sign-in accepted; English everywhere instead of the proposed Hungarian UI; toolbox container accepted; no attribution lines; no installation without agreement |
| Verification | Script check of anchors and point totals; the student merged PR #1 (no written remarks) |
| AI mistakes found | Technology versions and some provider capabilities were assumed without checking; the plan marks them as risks to verify at the start of each phase. The AI noticed before the first push that commits would have published a private e-mail address; the unpushed commits were rewritten with a noreply address |

## 2026-11-22 – Phase 0, foundation

| | |
|---|---|
| Task | Toolbox image, gates, git hooks, documentation skeleton |
| AI proposal | Split the toolbox into `lint` and `ops` targets instead of one large image |
| Human decision | The student merged PR #2 (no written remarks), then delegated later merges to the assistant and asked for the simplest implementation that meets the requirements |
| Verification | Versions and checksums taken from official releases (GitHub asset digests; for gitleaks, actionlint and hadolint also compared with the published checksum files); clean-clone run; negative tests ([evidence](../evidence/phase-00-foundation.md)) |
| AI mistakes found | The first hadolint checksum URL was guessed and did not exist; the correct file was then found in the release's asset list. shellcheck publishes no checksum file, so its value rests on the GitHub digest only |

## 2026-11-22 – Plan simplification

| | |
|---|---|
| Task | Reduce the plan after the student judged that it must not be overcomplicated |
| AI proposal | One backend image instead of three, one chart instead of two, direct staging commit instead of a self-approving PR, no OpenTofu module for GitHub, fewer workflows, test tools and SLOs |
| Human decision | The priority was set by the student; the individual cuts were chosen by the assistant |
| Verification | Every grading area still has a section and evidence in the traceability table |
| AI mistakes found | The first plan was oversized: it contained tools that no requirement needed |

## 2026-11-22 – Phase 1, walking skeleton and CI

| | |
|---|---|
| Task | Backend and web skeleton, Compose environments, CI |
| AI proposal | Synchronous database access, Caddy for both TLS proxy and static files, Biome instead of several linters |
| Human decision | None needed; merging was delegated beforehand |
| Verification | Unit, integration and smoke tests; CI on amd64; a deliberately broken PR turned red ([evidence](../evidence/phase-01-walking-skeleton.md)) |
| AI mistakes found | The migration lock was session-scoped and stayed on the pooled connection, so a second migration waited forever; the integration test hung and revealed it. The first test dependency choice (httpx) was deprecated by the framework; the replacement's origin was checked before adopting it. Several type errors were caught by mypy |

## 2026-11-22 – Phase 2, note-taking API

| | |
|---|---|
| Task | Accounts, hierarchy, versions, trash |
| AI proposal | SQLAlchemy Core instead of an ORM; hierarchy rules also enforced by database constraints |
| Human decision | The student asked for phases 2–6 without stops and stated that PR comments are pointless in a one-person project |
| Verification | 92 tests, coverage thresholds in CI, strict typing ([evidence](../evidence/phase-02-note-taking.md)) |
| AI mistakes found | A first draft made a dependency optional only to simplify tests; it was replaced by a required dependency with a lazily connecting engine |

## 2026-11-22 – Phase 3, user interface

| | |
|---|---|
| Task | Visual identity, editor, library, versions, trash |
| AI proposal | Milkdown after a fidelity spike; a framework-independent `PageSession` holding the autosave and conflict logic |
| Human decision | None needed |
| Verification | 34 unit and 20 browser tests, axe, screenshots inspected by the AI ([evidence](../evidence/phase-03-user-interface.md)) |
| AI mistakes found | TypeScript 7 was chosen although the type generator supports only 5.x. axe found a missing main heading. Screenshots showed an overlapping button on narrow screens that no test covered. One browser test wrongly expected a draft after a save that had in fact succeeded |

## 2026-11-22 – Phase 4, search

| | |
|---|---|
| Task | Job queue, indexing, embedder, hybrid search |
| AI proposal | e5-small as embedding model, `tokenizers` library |
| Human decision | None needed |
| Verification | Quality thresholds fixed before measuring; 144 backend and 23 browser tests; live outage exercise ([evidence](../evidence/phase-04-search.md)) |
| AI mistakes found | The planned model failed the quality thresholds and was replaced after a measured comparison. The tokenizer library took 285 MiB, found by measuring memory. A first fake embedding made all unrelated texts identical, so a test passed and failed for the wrong reasons. One commit was made without waiting for the result of `make check`; CI rejected it |

## 2026-11-22 – Phase 5, PDF export

| | |
|---|---|
| Task | PDF export, status, download, cleanup |
| AI proposal | Session-protected download instead of the planned signed link, to avoid another secret |
| Human decision | None needed |
| Verification | 164 backend and 25 browser tests, mutation check of the SSRF test, live `SIGKILL` exercise, pages inspected visually ([evidence](../evidence/phase-05-pdf-export.md)) |
| AI mistakes found | All worker threads took any kind of job, so a flood of indexing delayed exports by 31 s; only the live exercise showed it. A retry kept the job in the wrong state. `clip-path` is not supported by the renderer. A duration was first written into an ADR as an estimate and then replaced by a measurement |
