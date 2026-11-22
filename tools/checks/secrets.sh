#!/usr/bin/env bash
# Scans the full history and the uncommitted changes of tracked files for secrets.
set -euo pipefail

gitleaks git --redact --no-banner --log-level warn .
gitleaks git --redact --no-banner --log-level warn --staged .
gitleaks git --redact --no-banner --log-level warn --pre-commit .
echo "secrets: none found"
