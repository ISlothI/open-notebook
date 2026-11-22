# Phase 2 – Note-taking API

- **Date:** 2026-11-22
- **Commit:** `12babc8a`
- **CI run:** [45057668422](https://github.com/ISlothI/open-notebook/actions/runs/45057668422) (all jobs passed; JUnit and coverage files are attached as `test-reports`)

## Result of `make test`

```text
92 passed in 9.47s
TOTAL                                    865      7     64      1    99%
domain and application:
TOTAL                                    353      0     48      0   100%
```

Composition roots (`main.py`) are excluded from coverage; the smoke test runs them. High coverage shows which code was executed, not that every behaviour is right.

## Flows verified through the HTTP API against PostgreSQL 18

| Flow | Tests |
|---|---|
| F1 write, version, restore | `test_every_save_creates_a_version`, `test_old_version_can_be_read_and_restored` |
| F4 delete and recover | `test_trash_hides_the_subtree_and_restore_brings_it_back`, `test_every_kind_can_be_trashed_and_restored`, `test_restore_into_trashed_parent_needs_a_new_place` |
| R3 edit conflict | `test_conflicting_save_overwrites_nothing`, `test_concurrent_saves_let_exactly_one_win` |
| Access | `test_other_users_items_do_not_exist` (10 operations), session, rate limit and cross-site tests |
| Schema | migrations up and down, concurrent start, migrations equal table definitions |

The parts of F4 that concern search are verified in phase 4.
