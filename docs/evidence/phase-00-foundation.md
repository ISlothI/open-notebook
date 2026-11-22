# Phase 0 – Foundation

- **Date:** 2026-11-22
- **Commit:** `9777ed8`
- **Environment:** macOS on arm64, Docker 29.4.3, GNU Make 3.81, git 2.39.5

## 1. Clean clone needs only Docker, git and make

Fresh `git clone`, empty environment (`env -i`), a `PATH` limited to the system directories plus Docker, and an image rebuilt without cache. Tool availability on that `PATH`:

```text
docker: yes git: yes make: yes uv: no kubectl: no gh: no node: no helm: no gitleaks: no
```

```text
$ make toolbox TOOLBOX_BUILD_FLAGS="--no-cache --quiet"
sha256:e583ed3fb0489ee719092e3744c653396a87101eef4b44f51048b2e293074bf0
toolbox exit=0
$ make check
sha256:e583ed3fb0489ee719092e3744c653396a87101eef4b44f51048b2e293074bf0
secrets: none found
commit history: 10 commits valid
shellcheck: 8 files clean
hadolint: 1 files clean
actionlint: no files
gate tests: 17 passed, 0 failed
check exit=0
```

The working tree stayed clean afterwards. `actionlint` has nothing to check until the workflows arrive in phase 1.

## 2. Tampered download is refused

The gitleaks arm64 checksum was altered in a copy of `tools.lock`:

```text
/tmp/tmp.mGxwD2cFom/download: FAILED
sha256sum: WARNING: 1 computed checksum did NOT match
ERROR: process "/bin/sh -c bash /build/install-tools.sh /build/tools.lock \"${TARGETARCH}\" /opt/tools" did not complete successfully: exit code: 1
```

## 3. Tools can be installed for amd64

`docker build --platform linux/amd64 --target fetch tools/toolbox` (emulated; the download stage only, the checks were not run on amd64):

```text
installed gitleaks (amd64)
installed actionlint (amd64)
installed hadolint (amd64)
installed shellcheck (amd64)
```

## 4. Git hooks reject bad commits

```text
$ git commit -m "Added stuff"
commit message rejected: expected 'type(scope): imperative summary' with a known type and scope
  subject: Added stuff
exit=1
$ git commit -m "build: add skeleton" -m "Co-Authored-By: X <x@example.invalid>"
commit message rejected: attribution lines are not allowed
  subject: build: add skeleton
exit=1
```

## Interpretation

The "Done when" condition is met on one arm64 macOS machine. Running the full check on amd64 Linux is proven by CI in phase 1. Not measured here: behaviour with a Docker engine other than Docker Desktop.
