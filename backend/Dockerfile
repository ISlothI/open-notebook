# syntax=docker/dockerfile:1
FROM ghcr.io/astral-sh/uv:0.13.9@sha256:d3b601f0c7b118bc1753febf7c41cc80981df678445e0254284eecf84db79a7d AS uv

FROM python:3.13-slim-trixie@sha256:e48f59cdba69a3cbd9ed2cf0f348d90d45a8d350d98134cf1070bc106ee9ed90 AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/opt/venv/bin:$PATH
WORKDIR /app

# The embedding model (Apache-2.0), pinned by revision and checksum; nothing is downloaded at run time.
FROM scratch AS model
ARG TOKENIZER_URL=https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2/resolve/e8f8c211226b894fcb81acc59f3b34ba3efd5f42
ARG MODEL_URL=https://huggingface.co/Xenova/paraphrase-multilingual-MiniLM-L12-v2/resolve/2c4055b12046f11709e9df2c122e59ffbdc2f900
ADD --checksum=sha256:66fc00f5f29afcaff34092e1bdd20008ca3918265a82fb9695a551e510cc4ebc --chmod=444 ${MODEL_URL}/onnx/model_quantized.onnx /model.onnx
ADD --checksum=sha256:cfc8146abe2a0488e9e2a0c56de7952f7c11ab059eca145a0a727afce0db2865 --chmod=444 ${TOKENIZER_URL}/sentencepiece.bpe.model /sentencepiece.model

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
