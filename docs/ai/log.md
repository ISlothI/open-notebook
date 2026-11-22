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
