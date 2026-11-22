#!/bin/sh
# Updates backend/uv.lock with the uv and Python versions pinned in the Dockerfile.
set -eu

cd "$(dirname "$0")/../../backend"
image=$(docker build --quiet --target lock .)
docker run --rm --user "$(id -u):$(id -g)" --env HOME=/tmp --volume "$PWD:/app" "$image" uv lock "$@"
