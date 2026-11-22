# 0001 – Monorepo

- **Status:** Accepted
- **Date:** 2026-11-22

## Context

One person develops the application, its infrastructure and its deployment configuration. The evaluator must be able to verify everything from a single place.

## Decision

Application code, infrastructure code, desired deployment state and documentation live in one repository, separated by top-level directories.

## Alternatives

| Alternative | Why not |
|---|---|
| Separate repository per component | Synchronising versions and CI is overhead without independent teams |
| Separate GitOps repository | Cleaner access separation, but evidence is scattered and a cross-repository write credential would be needed |

## Consequences

- A change and its deployment configuration can be reviewed together.
- Workflows need path filters so that a desired-state change does not trigger a build.
- Write access to the repository covers both code and desired state; branch protection and the signed release chain limit this.
