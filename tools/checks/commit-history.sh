#!/usr/bin/env bash
# Validates every non-merge commit reachable from HEAD. Dependabot writes its own messages.
set -euo pipefail

checks_dir=$(cd "$(dirname "$0")" && pwd)
message_file=$(mktemp)
trap 'rm -f "$message_file"' EXIT

commits=$(git log --no-merges --perl-regexp --author='^(?!dependabot\[bot\])' --format=%H HEAD)
failures=0
for commit in $commits; do
  git log -1 --format=%B "$commit" > "$message_file"
  if ! bash "$checks_dir/commit-message.sh" "$message_file"; then
    echo "  commit: $commit" >&2
    failures=$((failures + 1))
  fi
done

[ "$failures" -eq 0 ] || exit 1
echo "commit history: $(echo "$commits" | wc -l | tr -d ' ') commits valid"
