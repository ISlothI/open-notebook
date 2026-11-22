# Phase 6 – Supply chain

- **Date:** 2026-11-22
- **Commit:** `35f1017`
- **Release:** 0.1.1, [run 45065259417](https://github.com/ISlothI/open-notebook/actions/runs/45065259417) (SBOMs and vulnerability reports are attached)
- **CI run of the change:** [45064996382](https://github.com/ISlothI/open-notebook/actions/runs/45064996382)

## 1. Verification on an independent machine, without any login

`tools/release/verify.sh 0.1.1` on the development machine (arm64):

```text
signature valid: open-notebook-backend:0.1.1
signature valid: open-notebook-web:0.1.1
signature valid: open-notebook-database:0.1.1
signature valid: charts/open-notebook:0.1.1
SBOM attestation valid: open-notebook-backend:0.1.1
SBOM attestation valid: open-notebook-web:0.1.1
SBOM attestation valid: open-notebook-database:0.1.1
unsigned artifact refused: open-notebook-backend:0.1.1-amd64
```

A wrong signer is refused:

```text
Error: no matching attestations: failed to verify certificate identity: no matching CertificateIdentity found,
last error: expected SAN value "https://github.com/somebody/else/.github/workflows/release.yml@refs/heads/main", ...
```

Build provenance (`gh attestation verify`):

```text
https://slsa.dev/provenance/v1 builder=https://github.com/ISlothI/open-notebook/.github/workflows/release.yml@refs/heads/main commit=35f10170
```

Platforms of the backend image: `linux/amd64 linux/arm64`. The published chart refers to all three images by digest. Deployment of an unsigned chart to a cluster is tried in phase 8.

## 2. Vulnerability gate

| Image | Fixable HIGH/CRITICAL before | After |
|---|---:|---|
| backend | 6 | 0 |
| web | 1 | 0, with one documented exception until 2027-02-28 |
| database | 27 (upstream image) | 0 |

The gate refuses the upstream database image: `Total: 1` and `Total: 26`, exit code 1. Findings without an available fix do not stop a release; they are in the attached reports.

## 3. SBOM and static analysis

The SBOM of the backend lists 160 packages (SPDX 2.3). CodeQL reports no open alert for Python, TypeScript and the workflows.

## 4. Update proposals are judged by the same gates

| Dependabot PR | CI | Consequence |
|---|---|---|
| #11 TypeScript 7 | failed | ignored: the type generator supports only version 5 |
| #12 Python 3.15 | failed | ignored: raised together with the lockfile by hand |
| #13 Python packages | passed | merged |
