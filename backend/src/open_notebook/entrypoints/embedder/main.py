"""Composition root of the embedder process."""

import uvicorn

from open_notebook.entrypoints.embedder.app import create_app
from open_notebook.infrastructure.build_info import publish_build_info
from open_notebook.infrastructure.logging import configure_logging
from open_notebook.infrastructure.onnx_embedder import OnnxEmbedder
from open_notebook.settings import ProcessSettings

SERVICE = "embedder"
PORT = 8001
MODEL_THREADS = 2


def main() -> None:
    settings = ProcessSettings()
    configure_logging(settings, SERVICE)
    publish_build_info(SERVICE, settings.version)
    uvicorn.run(
        create_app(OnnxEmbedder(MODEL_THREADS), settings.version),
        host="0.0.0.0",  # noqa: S104 - the container network is the boundary
        port=PORT,
        log_config=None,
        access_log=False,
    )
