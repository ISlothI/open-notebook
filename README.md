# Open Notebook

A structured, Markdown-based note-taking application with page versions, trash, hybrid search and PDF export, built together with a reproducible development and operations process.

> **Status:** under development, see the [project plan](docs/project-plan.md). This README describes only what already works: accounts, the library, the page editor, versions, trash, search and PDF export.

## Prerequisites

| Tool | Needed for |
|---|---|
| Docker (running, with BuildKit) | every tool runs in a container |
| git | source control |
| GNU Make 3.81 or newer | entry point of all tasks |

Nothing else has to be installed. Building the toolbox image for the first time needs internet access.

## Quick start

```sh
git clone https://github.com/ISlothI/open-notebook.git
cd open-notebook
make dev     # development environment with hot reload
make smoke   # verify it from outside, through TLS
```

Then open <https://localhost:9443>. The certificate is issued by a local CA created on the first start, so the browser shows a warning; `make smoke` verifies the certificate against that CA. `make up` starts the same stack with production images, `make down` stops it and keeps the data.

## Checks

`make test` runs the unit and integration tests against a throw-away PostgreSQL and enforces the coverage thresholds. `make e2e` runs the browser tests against the running application (`make up`). Reports are written to `.local/reports/`.

`make check` runs every gate in containers, without network access and as a non-root user. The tools come from the checksum-verified [toolbox](tools/toolbox/Dockerfile) and the development images:

| Target | What it checks |
|---|---|
| `make secrets` | no secret in the git history, staged or unstaged changes (gitleaks) |
| `make commits` | every commit message follows Conventional Commits |
| `make lint` | shell scripts, Dockerfiles and GitHub workflows |
| `make test-gates` | the gates above really reject bad input |
| `make check-backend` | format, lint, types, unit tests of the Python code |
| `make check-web` | format, lint, types, unit tests of the web application |

`make help` lists all targets. Contributors enable the git hooks once per clone with `make hooks`.

## Repository

| Path | Content |
|---|---|
| [backend/](backend/) | Python package of the api, worker and embedder, migrations, tests |
| [web/](web/) | React application |
| [compose/](compose/) | local environments and reverse proxy |
| [.github/workflows/](.github/workflows/) | continuous integration |
| [CLAUDE.md](CLAUDE.md) | requirements and working rules, also the instructions of the AI assistant |
| [docs/](docs/) | plan, [decisions](docs/adr/README.md), [security](docs/security.md), [AI log](docs/ai/log.md), [evidence](docs/evidence/) |
| [tools/](tools/) | toolbox image, checks and their tests |
