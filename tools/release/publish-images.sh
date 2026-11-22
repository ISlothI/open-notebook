#!/usr/bin/env bash
# Joins the images built per architecture, and signs and describes the result.
# Writes "<name>=<digest>" lines to the file given as the second argument.
set -euo pipefail

version=$1
digests_file=$2
: "${REGISTRY:?}" "${REPORT_DIR:?}" "${TOOLBOX:?}"

: > "$digests_file"
for name in backend web database; do
  image="$REGISTRY/open-notebook-$name"
  docker buildx imagetools create --tag "$image:$version" \
    "$image:$version-amd64" "$image:$version-arm64"
  digest=$(docker buildx imagetools inspect "$image:$version" --format '{{.Manifest.Digest}}')

  for architecture in amd64 arm64; do
    $TOOLBOX syft scan --quiet --platform "linux/$architecture" "registry:$image@$digest" \
      --output "spdx-json=$REPORT_DIR/$name-$architecture.spdx.json"
  done

  $TOOLBOX cosign sign --yes "$image@$digest"
  for architecture in amd64 arm64; do
    $TOOLBOX cosign attest --yes --type spdxjson \
      --predicate "$REPORT_DIR/$name-$architecture.spdx.json" "$image@$digest"
  done
  echo "$name=$digest" >> "$digests_file"
done
