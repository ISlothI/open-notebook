# syntax=docker/dockerfile:1
FROM pgvector/pgvector:pg18-trixie@sha256:ab49524d18df7200b74ac9a475e1db6297fc1eb57da4c214c63d10ecc4b754fa
# The server never runs as root, so the vulnerable helper that drops root is not needed.
# Only the named package is upgraded, so that the PostgreSQL version stays pinned by the digest.
# Debian removes superseded versions, so pinning it would break rebuilds. Review by 2027-06-30.
# hadolint ignore=DL3008
RUN rm /usr/local/bin/gosu \
  && apt-get update \
  && apt-get install --yes --no-install-recommends --only-upgrade zlib1g \
  && rm -rf /var/lib/apt/lists/*
USER 999:999
