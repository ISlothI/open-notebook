# Open Notebook – working guide

University assignment for the "Cloud and DevOps Basics" practical course: a OneNote-like note-taking application with a reproducible development and operations process built around it. **What is graded is primarily the DevOps process and its evidence**, but the application itself must also have the quality of a paid product.

The detailed plan is [docs/project-plan.md](docs/project-plan.md). If code and plan disagree, fix one of them; the discrepancy must not stay.

## 1. Requirements

### Mandatory conditions (missing any of them means failing)

1. The project is **reproducible in a clean environment**.
2. There is **no real credential** in the repository, git history, images or logs.
3. At least one user flow is **verified by an automated check**.
4. At least 30 of 60 points (the target is 60).

### Grading

| # | Area | Points |
|---|---|---:|
| G1 | Meaningful system sized for one person, justified architecture | 5 |
| G2 | Reproducible local environment and clear repository | 5 |
| G3 | Automated tests and continuous integration | 9 |
| G4 | Artifact management, security scanning, SBOM and secret management | 7 |
| G5 | Declarative deployment, separated environments, version change and rollback | 9 |
| G6 | CD/GitOps: desired state in Git and automated release management | 5 |
| G7 | IaC and configuration management decisions, reproducibility | 5 |
| G8 | Metrics, logging, dashboard and SLI/SLO | 7 |
| G9 | Reliability and recovery evidence | 4 |
| G10 | Professional verification of the AI-assisted workflow | 4 |

- The number of tools does not matter. Every technology is justified by a need of the system; when an alternative is chosen, document how the expected capability is met.
- The system needs: a user or API entry point, durable storage, meaningful additional processing, and at least three documented user flows including a failure or recovery path.
- Deliverables: source code, deployment configuration, README (operation and reproduction), architecture and decisions, evidence of automated checks, observability results, an exercised recovery procedure, short professional AI-usage documentation.
- There is no presentation and no intermediate milestone: **only what can be verified from the repository counts.**
- No paid cloud service; everything runs locally or on free GitHub services.

### Features (the student's specification)

1. **Hierarchical notes**: folders, notebooks, sections, pages. Page content is Markdown.
2. **Page versions**: every save creates a new version; any earlier version can be restored.
3. **Trash**: deleted folders, notebooks, sections and pages can be restored.
4. **Hybrid search** (semantic and full-text) across all notebooks, filterable by notebook; indexing is done by a worker.
5. **PDF export**: a page or a whole notebook, with table of contents; background job, trackable status, download link.
6. **Look and feel**: aesthetic and functional, inspired by Apple's clarity, but with its own mood and logo.

Approved addition: minimal sign-in (e-mail, password, session). Anything beyond this needs the student's approval.

## 2. Collaboration rules

- **Language**: the code, the UI, all documentation, commits and PRs are in English. Conversation with the student is in Hungarian.
- **Ask before installing anything.** The machine has Docker Desktop, git, make, Python 3.11, uv, kubectl and gh. Every other tool runs from a container (toolbox). If that is not enough, ask first.
- **What can only be done on a user interface** is requested from the student: exact steps, and how to recognise success.
- **Before phase 7, remind the student** to raise Docker Desktop memory to 5 GB, and wait for confirmation.
- **Commit regularly**, in small, self-contained, green units.
- **No AI attribution in commits or PRs**: no `Co-Authored-By`, "Generated with" or similar line. AI usage is documented in `docs/ai/` instead.
- Pushing branches and opening PRs is allowed. **Merging into `main` is done by the student.** Other remote changes (repository settings, deletions, force-push) need permission.
- **Privacy**: the repository is public; the student's personal data (e-mail, local paths) must not get into files, logs or evidence.
- **Resource limits**: 8 GB RAM, about 3.8 GiB for the Docker VM, about 27 GB free disk. Recalculate the plan's memory budget before adding a component.
- Delete a Docker volume, image or cluster only if it belongs to this project. The machine holds other projects' volumes: **`docker system prune` and `docker volume prune` are forbidden.**

## 3. Engineering principles

- **SOLID, clean code**: ports and adapters; the domain imports no framework, database or HTTP. Small single-responsibility modules, expressive names. A comment explains "why".
- **YAGNI**: an abstraction needs a real second implementation or a test substitute.
- **Types**: Python `mypy --strict`, TypeScript `strict`. No `Any`/`any` without justification.
- **Tests**: behaviour and its test are in the same commit. A failing test precedes a bug fix. Flaky tests are fixed, not re-run.
- **Migrations**: expand/contract only, because after an application rollback the old code must run on the new schema.
- **12-factor**: configuration from environment variables, stateless processes, logs to stdout.

## 4. DevOps principles

- **Everything in Git**: manual `kubectl edit`/`apply` of the application is forbidden; a change goes through PR, CI and Flux.
- **Build once**: exactly the artifact that ran on staging goes to prod. Images are referenced by digest; `latest` is never used.
- **Pinning**: a lockfile for every language; base images by digest; GitHub Actions by full commit SHA; downloaded binaries by SHA-256. Verify versions from an official source at the start of the phase; never write them from memory.
- **Least privilege**: `permissions` per workflow; non-root containers, read-only root filesystem, all capabilities dropped; default-deny NetworkPolicy.
- **Secrets**: generated per cluster at installation; neither in Git nor in OpenTofu state. Update the inventory in `docs/security.md` when adding one.
- **Idempotence**: every `make` target and Ansible playbook can be re-run; the second run is `changed=0`.
- **Observability ships with the feature**: a new endpoint or job type comes with a metric, a structured log and a correlation ID.
- **Checks are not switched off**: exceptions need a justification and an expiry date (e.g. `.trivyignore.yaml`).

## 5. Workflow

1. Read the next phase in the plan; work on one phase at a time.
2. Branch: `feat/…`, `fix/…`, `ci/…`, `docs/…` (`main` changes only through PRs).
3. Implement and test; `make check` is green before every commit.
4. **Conventional Commits**: `type(scope): imperative summary`.
   - Types: `feat fix refactor perf test docs build ci chore revert`
   - Scopes: `api worker embedder web db deploy infra ci obs security docs`
5. At the end of a phase, prove every "Done when" item with an **executed command**, store the output under `docs/evidence/`, update the status table of the plan and the AI log, then open a PR.
6. Important decisions get an ADR: `docs/adr/NNNN-title.md` (context, decision, alternatives, consequences).

## 6. Evidence and honesty

- Do not claim that something works unless it was run. Always distinguish estimates from measurements.
- Evidence contains: date, commit SHA, command, raw output or a CI run link, short interpretation.
- Failed exercises are documented too, with the lesson learned; results are not embellished afterwards.
- **AI log** (`docs/ai/log.md`): task, AI proposal, human decision, verification method, AI mistake found. Record a human review only if the student actually did it.

## 7. Planned commands

Created during the phases; the README must not advertise what does not exist yet.

| Command | Purpose |
|---|---|
| `make dev` | full development environment in Compose |
| `make check` | lint, type check, unit tests, secret scan |
| `make test` / `make e2e` | integration / browser tests |
| `make cluster` / `make cluster-down` | create / delete the local Kubernetes cluster |
| `make backup` / `make restore` / `make drill` | backup / restore / full DR exercise |
| `make load` | load test with SLO thresholds |
