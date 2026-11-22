# 0009 – Signed chart as the unit of release

- **Status:** Accepted
- **Date:** 2026-11-22

## Context

A release consists of three images and the deployment configuration. What was tested on staging must be exactly what runs in production, and the cluster must accept only what this repository's pipeline produced.

## Decision

The release workflow builds and scans the images per architecture on native runners, joins them, attests their SBOM and provenance, signs them keylessly with cosign, writes their digests into the Helm chart, and publishes and signs the chart as an OCI artifact. The version is `VERSION` plus the run number. An environment refers only to the chart version; because the chart contains the digests, its signature covers the images as well.

## Alternatives

| Alternative | Why not |
|---|---|
| Image tags updated separately | Nothing guarantees that they belong together; tags can be moved |
| Long-lived signing key | One more secret to protect and rotate |
| Rebuilding for production | The tested and the released artifact would differ |

## Consequences

- No secret is stored: the registry uses the run's token, signing its identity.
- Signatures are recorded in the public transparency log, which is acceptable for a public repository.
- The release depends on the availability of GitHub and Sigstore; running environments do not.
- The database image is ours as well: the upstream image had 27 fixable HIGH or CRITICAL findings, 26 of them in a helper that is not needed.
