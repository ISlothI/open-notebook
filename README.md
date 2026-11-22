# Open Notebook

A structured, Markdown-based note-taking application with page versions, trash, hybrid search and PDF export, built together with a reproducible development and operations process.

> **Status:** phase 0 (foundation) of the [project plan](docs/project-plan.md). The application itself is not implemented yet; this README describes only what already works.

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
make check
```

`make check` builds the [toolbox](tools/toolbox/Dockerfile) image from checksum-verified tools and runs every gate in it, without network access and as a non-root user:

| Target | What it checks |
|---|---|
| `make secrets` | no secret in the git history, staged or unstaged changes (gitleaks) |
| `make commits` | every commit message follows Conventional Commits |
| `make lint` | shell scripts, Dockerfiles and GitHub workflows |
| `make test-gates` | the gates above really reject bad input |

`make help` lists all targets. Contributors enable the git hooks once per clone with `make hooks`.

## Repository

| Path | Content |
|---|---|
| [CLAUDE.md](CLAUDE.md) | requirements and working rules, also the instructions of the AI assistant |
| [docs/](docs/) | plan, [decisions](docs/adr/README.md), [security](docs/security.md), [AI log](docs/ai/log.md), [evidence](docs/evidence/) |
| [tools/](tools/) | toolbox image, checks and their tests |
