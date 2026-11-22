"""Composition root of the api process."""

import uvicorn
from fastapi import FastAPI

from open_notebook.entrypoints.api.app import create_app
from open_notebook.infrastructure.build_info import publish_build_info
from open_notebook.infrastructure.database import DatabaseProbe, build_engine
from open_notebook.infrastructure.logging import configure_logging
from open_notebook.settings import Settings

SERVICE = "api"


def build() -> FastAPI:
    settings = Settings()
    configure_logging(settings, SERVICE)
    publish_build_info(SERVICE, settings.version)
    return create_app(DatabaseProbe(build_engine(settings)), settings.version)


def main() -> None:
    uvicorn.run(
        "open_notebook.entrypoints.api.main:build",
        factory=True,
        host="0.0.0.0",  # noqa: S104 - the container network is the boundary
        port=Settings().api_port,
        log_config=None,
        access_log=False,
    )
