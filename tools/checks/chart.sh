#!/usr/bin/env bash
# Renders the chart and validates it against the Kubernetes schemas and security rules.
set -euo pipefail

chart=deploy/chart
kubernetes_version=1.37.0
rendered=$(mktemp -d)
trap 'rm -rf "$rendered"' EXIT

helm lint --quiet --strict "$chart"
helm template open-notebook "$chart" --set api.replicas=2 > "$rendered/manifests.yaml"
kubeconform -strict -summary -kubernetes-version "$kubernetes_version" "$rendered/manifests.yaml"
