#!/usr/bin/env bash
# Lints the shell scripts, Dockerfiles and workflows known to git.
set -euo pipefail

list_files() {
  git ls-files --cached --others --exclude-standard -- "$@"
}

run_linter() {
  local linter=$1 files=$2
  if [ -z "$files" ]; then
    echo "$linter: no files"
    return
  fi
  echo "$files" | xargs -d '\n' "$linter"
  echo "$linter: $(echo "$files" | wc -l) files clean"
}

run_linter shellcheck "$(list_files '*.sh' '.githooks/*')"
run_linter hadolint "$(list_files 'Dockerfile' '*/Dockerfile')"
run_linter actionlint "$(list_files '.github/workflows/*.yml' '.github/workflows/*.yaml')"
