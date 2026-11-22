#!/usr/bin/env bash
# Fails if the image archive on stdin has a fixable HIGH or CRITICAL vulnerability.
set -euo pipefail

name=$1
report_dir=$2
archive=$(mktemp)
trap 'rm -f "$archive"' EXIT
cat > "$archive"

scan() {
  trivy image --quiet --cache-dir /cache --input "$archive" --scanners vuln \
    --ignorefile .trivyignore.yaml --show-suppressed "$@"
}

# The report lists everything; the gate considers only what can be fixed.
scan --format json --output "$report_dir/$name-vulnerabilities.json"
echo "scanning $name"
scan --severity HIGH,CRITICAL --ignore-unfixed --table-mode detailed --exit-code 1
