#!/usr/bin/env bash
# Proves that the gates accept good input and, more importantly, reject bad input.
set -euo pipefail

tests_dir=$(cd "$(dirname "$0")" && pwd)
checks_dir=$tests_dir/../checks
work_dir=$(mktemp -d)
trap 'rm -rf "$work_dir"' EXIT
passed=0
failed=0

report() {
  if [ "$1" = "$2" ]; then
    passed=$((passed + 1))
  else
    failed=$((failed + 1))
    echo "FAILED: $3 (expected $1, got $2)" >&2
  fi
}

outcome_of() {
  if "$@" > "$work_dir/output" 2>&1; then echo accepted; else echo rejected; fi
}

expect_message() {
  printf '%b' "$2" > "$work_dir/message"
  report "$1" "$(outcome_of bash "$checks_dir/commit-message.sh" "$work_dir/message")" "message: $2"
}

new_repository() {
  git init --quiet "$1"
  git -C "$1" config user.name test
  git -C "$1" config user.email test@example.invalid
}

commit_file() {
  printf '%s\n' "$2" > "$1/settings.txt"
  git -C "$1" add settings.txt
  git -C "$1" commit --quiet --message "$3"
}

expect_in_repository() {
  report "$1" "$(cd "$2" && outcome_of bash "$checks_dir/$3")" "$4"
}

test_commit_messages() {
  expect_message accepted 'feat(api): add page versions\n'
  expect_message accepted 'docs: explain recovery\n\nLonger body.\n'
  expect_message accepted 'feat(db)!: drop legacy column\n'
  expect_message rejected 'added stuff\n'
  expect_message rejected 'feature(api): unknown type\n'
  expect_message rejected 'feat(kitchen): unknown scope\n'
  expect_message rejected 'fix(api): trailing period.\n'
  expect_message rejected 'fix(api):missing space\n'
  expect_message rejected "fix(api): $(printf 'x%.0s' {1..80})\\n"
  expect_message rejected 'feat(api): add x\n\nCo-Authored-By: Someone <a@example.invalid>\n'
  expect_message rejected 'feat(api): add x\n\nGenerated with a tool\n'
}

test_commit_history() {
  local repository=$work_dir/history
  new_repository "$repository"
  commit_file "$repository" one 'feat: add first file'
  expect_in_repository accepted "$repository" commit-history.sh 'valid history'
  commit_file "$repository" two 'oops'
  commit_file "$repository" three 'fix: repair file'
  expect_in_repository rejected "$repository" commit-history.sh 'invalid commit in the middle'
}

test_secret_scan() {
  local repository=$work_dir/secrets fake_token
  # Assembled at run time, so that the repository itself contains no token-like text.
  fake_token="ghp_$(head -c 4096 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | head -c 36)"
  new_repository "$repository"
  commit_file "$repository" 'colour = blue' 'feat: add settings'
  expect_in_repository accepted "$repository" secrets.sh 'clean repository'

  printf 'token = "%s"\n' "$fake_token" > "$repository/settings.txt"
  expect_in_repository rejected "$repository" secrets.sh 'unstaged secret'
  git -C "$repository" add settings.txt
  expect_in_repository rejected "$repository" secrets.sh 'staged secret'
  git -C "$repository" commit --quiet --message 'feat: leak token'
  commit_file "$repository" 'colour = blue' 'fix: remove token'
  expect_in_repository rejected "$repository" secrets.sh 'secret only in history'
}

test_commit_messages
test_commit_history
test_secret_scan

echo "gate tests: $passed passed, $failed failed"
[ "$failed" -eq 0 ]
