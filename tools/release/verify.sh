#!/usr/bin/env bash
# Proves that a release is signed by this repository's release workflow, and that the check
# refuses an artifact without a signature.
set -euo pipefail

version=$1
: "${REGISTRY:?}" "${TOOLBOX:?}" "${REPOSITORY:?}"

verify() {
  $TOOLBOX cosign "$@" \
    --certificate-oidc-issuer https://token.actions.githubusercontent.com \
    --certificate-identity "https://github.com/$REPOSITORY/.github/workflows/release.yml@refs/heads/main"
}

for artifact in open-notebook-backend open-notebook-web open-notebook-database charts/open-notebook; do
  verify verify "$REGISTRY/$artifact:$version" > /dev/null
  echo "signature valid: $artifact:$version"
done

for image in backend web database; do
  verify verify-attestation --type spdxjson "$REGISTRY/open-notebook-$image:$version" > /dev/null
  echo "SBOM attestation valid: open-notebook-$image:$version"
done

# The image of a single architecture is an intermediate artifact and is never signed.
if verify verify "$REGISTRY/open-notebook-backend:$version-amd64" > /dev/null 2>&1; then
  echo "an unsigned artifact was accepted" >&2
  exit 1
fi
echo "unsigned artifact refused: open-notebook-backend:$version-amd64"
