#!/usr/bin/env bash
# Validates one commit message file: Conventional Commits, no attribution trailers.
# Must stay compatible with Bash 3.2, because the git hook runs it on the host.
set -euo pipefail

readonly types='feat|fix|refactor|perf|test|docs|build|ci|chore|revert'
readonly scopes='api|worker|embedder|web|db|deploy|infra|ci|obs|security|docs'
readonly subject_pattern="^($types)(\\(($scopes)\\))?!?: [^ ].*[^. ]$"
readonly attribution_pattern='^[[:space:]]*(co-authored-by:|([^[:alnum:]]*)generated (with|by) )'
readonly max_subject_length=72

message_file=$1
message=$(grep -v '^#' "$message_file" || true)
subject=$(printf '%s\n' "$message" | head -n 1)

fail() {
  echo "commit message rejected: $1" >&2
  echo "  subject: $subject" >&2
  exit 1
}

[[ $subject =~ $subject_pattern ]] || fail "expected 'type(scope): imperative summary' with a known type and scope"
[ "${#subject}" -le "$max_subject_length" ] || fail "subject is longer than $max_subject_length characters"
if printf '%s\n' "$message" | grep -Eiq "$attribution_pattern"; then
  fail "attribution lines are not allowed"
fi
