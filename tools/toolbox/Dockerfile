# syntax=docker/dockerfile:1
ARG BASE_IMAGE=debian:trixie-slim@sha256:a72b4433de1cf7d6bae0c4cee74d0547f58601a643b3375f070c51600d63b6b2

FROM ${BASE_IMAGE} AS fetch
ARG TARGETARCH
# Debian removes superseded package versions, so pinning them would break rebuilds.
# The base image digest limits the drift. Review this exception by 2027-06-30.
# hadolint ignore=DL3008
RUN apt-get update \
  && apt-get install --yes --no-install-recommends ca-certificates curl \
  && rm -rf /var/lib/apt/lists/*
COPY tools.lock install-tools.sh /build/

FROM fetch AS fetch-lint
RUN bash /build/install-tools.sh /build/tools.lock "${TARGETARCH}" /opt/tools \
  actionlint gitleaks hadolint shellcheck

FROM fetch AS fetch-ops
RUN bash /build/install-tools.sh /build/tools.lock "${TARGETARCH}" /opt/tools \
  cosign helm kubeconform syft trivy

FROM ${BASE_IMAGE} AS lint
# Same exception as above. Review by 2027-06-30.
# hadolint ignore=DL3008
RUN apt-get update \
  && apt-get install --yes --no-install-recommends git \
  && rm -rf /var/lib/apt/lists/* \
  && git config --system --add safe.directory /workspace
COPY --from=fetch-lint /opt/tools/ /usr/local/bin/
ENV HOME=/tmp
WORKDIR /workspace
USER 65532:65532
CMD ["bash"]

FROM lint AS ops
COPY --from=fetch-ops /opt/tools/ /usr/local/bin/
# Root certificates for the tools that talk to registries.
COPY --from=fetch /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt
