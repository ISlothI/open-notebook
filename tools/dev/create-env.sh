#!/bin/sh
# Creates .env with random local credentials; an existing file is never changed.
set -eu

env_file=$1
[ ! -e "$env_file" ] || exit 0

umask 077
password=$(LC_ALL=C tr -dc 'A-Za-z0-9' < /dev/urandom | head -c 32)
printf 'POSTGRES_PASSWORD=%s\n' "$password" > "$env_file"
echo "created $env_file with random local credentials"
