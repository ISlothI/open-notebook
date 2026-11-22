#!/usr/bin/env bash
# Packages the chart with the image digests, publishes and signs it. Prints its digest.
set -euo pipefail

version=$1
digests_file=$2
: "${REGISTRY:?}" "${TOOLBOX:?}"

work_dir=.local/release
rm -rf "$work_dir/chart"
mkdir -p "$work_dir"
cp -R deploy/chart "$work_dir/chart"

while IFS='=' read -r name digest; do
  placeholder="$(echo "$name" | tr '[:lower:]' '[:upper:]')_DIGEST"
  sed -i.bak "s|sha256:$placeholder|$digest|" "$work_dir/chart/values.yaml"
done < "$digests_file"
rm -f "$work_dir/chart/values.yaml.bak"

if grep -q '_DIGEST' "$work_dir/chart/values.yaml"; then
  echo "an image digest is missing from the chart" >&2
  exit 1
fi

$TOOLBOX helm package --version "$version" --app-version "$version" \
  --destination "$work_dir" "$work_dir/chart" >&2
pushed=$($TOOLBOX helm push "$work_dir/open-notebook-$version.tgz" "oci://$REGISTRY/charts" 2>&1)
echo "$pushed" >&2
digest=$(echo "$pushed" | awk '/^Digest:/ {print $2}')
$TOOLBOX cosign sign --yes "$REGISTRY/charts/open-notebook@$digest" >&2
echo "$digest"
