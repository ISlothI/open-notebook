#!/bin/sh
# Generates the web client's types from the api's OpenAPI description.
# With --check, only reports whether the committed types are up to date.
set -eu

cd "$(dirname "$0")/../.."
work_dir=.local/api-types
mkdir -p "$work_dir"

docker run --rm --network none \
  --env ON_DATABASE_HOST=unused --env ON_DATABASE_NAME=unused \
  --env ON_DATABASE_USER=unused --env ON_DATABASE_PASSWORD=unused \
  open-notebook-backend:dev \
  python -c 'import json; from open_notebook.entrypoints.api.main import build; print(json.dumps(build().openapi()))' \
  > "$work_dir/openapi.json"

docker run --rm --network none --user "$(id -u):$(id -g)" --env HOME=/tmp \
  --volume "$PWD/$work_dir:/work" open-notebook-web:dev \
  npx --no-install openapi-typescript /work/openapi.json --output /work/schema.ts > /dev/null

if [ "${1:-}" = "--check" ]; then
  cmp "$work_dir/schema.ts" web/src/api/schema.ts || {
    echo "web/src/api/schema.ts is stale; run make api-types" >&2
    exit 1
  }
  echo "api types are up to date"
else
  cp "$work_dir/schema.ts" web/src/api/schema.ts
fi
