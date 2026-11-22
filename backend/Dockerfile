# syntax=docker/dockerfile:1
FROM ghcr.io/astral-sh/uv:0.13.9@sha256:d3b601f0c7b118bc1753febf7c41cc80981df678445e0254284eecf84db79a7d AS uv

FROM python:3.15-slim-trixie@sha256:65a65fc7b30b06cb6df4930fd4650697cb23f4c2698ab81fc87e4b031bc36928 AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    XDG_CACHE_HOME=/tmp/cache \
    PATH=/opt/venv/bin:$PATH
WORKDIR /app
# Debian removes superseded package versions, so pinning them would break rebuilds.
# The base image digest limits the drift. Review this exception by 2027-06-30.
# zlib1g is upgraded because the base image has a vulnerable version; pip is not needed.
# hadolint ignore=DL3008
RUN apt-get update \
  && apt-get install --yes --no-install-recommends \
    fonts-dejavu-core libharfbuzz-subset0 libpango-1.0-0 libpangoft2-1.0-0 zlib1g \
  && rm -rf /var/lib/apt/lists/* \
  && rm -rf /usr/local/lib/python3.13/site-packages/pip* \
    /usr/local/lib/python3.13/ensurepip /usr/local/bin/pip*
# The book face of the PDF (SIL Open Font License), the same family as on the web.
ADD --checksum=sha256:8a08d13f8a6c0d51be379a60af84f945f65369a67e509ee3c3bdcc421254d7c1 --chmod=444 https://raw.githubusercontent.com/google/fonts/8b0a1d0f5983c89bc2b93f1b5fb55f9e252744b5/ofl/newsreader/Newsreader%5Bopsz,wght%5D.ttf /usr/local/share/fonts/Newsreader.ttf
ADD --checksum=sha256:796668611f80b64d5adf182fde3b6f29ed83b4e7cbec7b96937e84ac01364792 --chmod=444 https://raw.githubusercontent.com/google/fonts/8b0a1d0f5983c89bc2b93f1b5fb55f9e252744b5/ofl/newsreader/Newsreader-Italic%5Bopsz,wght%5D.ttf /usr/local/share/fonts/Newsreader-Italic.ttf
RUN fc-cache --force

# The embedding model (Apache-2.0), pinned by revision and checksum; nothing is downloaded at run time.
FROM scratch AS model
ADD --checksum=sha256:66fc00f5f29afcaff34092e1bdd20008ca3918265a82fb9695a551e510cc4ebc --chmod=444 https://huggingface.co/Xenova/paraphrase-multilingual-MiniLM-L12-v2/resolve/2c4055b12046f11709e9df2c122e59ffbdc2f900/onnx/model_quantized.onnx /model.onnx
ADD --checksum=sha256:cfc8146abe2a0488e9e2a0c56de7952f7c11ab059eca145a0a727afce0db2865 --chmod=444 https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2/resolve/e8f8c211226b894fcb81acc59f3b34ba3efd5f42/sentencepiece.bpe.model /sentencepiece.model

FROM base AS lock
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_PYTHON_DOWNLOADS=never
USER 65532:65532

FROM base AS builder
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --locked --no-dev --no-install-project
COPY src ./src
RUN --mount=type=cache,target=/root/.cache/uv uv sync --locked --no-dev --no-editable

# Development tools and tests; the project is installed editable for hot reload.
FROM builder AS dev
COPY --from=model / /opt/model/
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv uv sync --locked
USER 65532:65532
CMD ["open-notebook-api"]

FROM base AS runtime
ARG VERSION=dev
ENV ON_VERSION=${VERSION}
COPY --from=model / /opt/model/
COPY --from=builder /opt/venv /opt/venv
COPY alembic.ini ./
COPY migrations ./migrations
USER 65532:65532
CMD ["open-notebook-api"]
