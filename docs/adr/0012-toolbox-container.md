# 0012 – Toolbox container

- **Status:** Accepted
- **Date:** 2026-11-22

## Context

The checks and operations tasks need many command-line tools. The evaluator's machine is unknown, the development machine has few tools, and installing more on it is to be avoided. Local and CI results must not differ because of tool versions.

## Decision

Tools run from one multi-stage Dockerfile. The base image is pinned by digest and every downloaded binary by version and SHA-256 for `amd64` and `arm64` in `tools/toolbox/tools.lock`. The `lint` target contains only what the checks need; an `ops` target with the Kubernetes and infrastructure tools is added in the phase that first needs it.

Checks run without network access, as the calling user, with all capabilities dropped and without the Docker socket.

## Alternatives

| Alternative | Why not |
|---|---|
| Host installation (Homebrew, apt) | Versions differ between machines; requires installation |
| Version manager (mise, asdf) | Good pinning, but still installs on the host |
| Official image per tool | Many images to pin and pull; no common environment for scripts |
| Dev container | Ties the workflow to specific editors |

## Consequences

- Only Docker, git and make are required.
- The first run takes longer because the image is built.
- Debian packages (git, curl) are not pinned to exact versions, because Debian removes superseded ones; the base image digest limits the drift. The linter exception has a review date.
- Updating a tool means changing two lines per tool in the lock file, after checking the official release.
- The future `ops` target will mount the Docker socket, which equals administrator access to the host. It will be limited to the targets that need it.
