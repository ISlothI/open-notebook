"""Builds the HTTP application from its dependencies."""

from fastapi import FastAPI

from open_notebook.entrypoints.api.health import AvailabilityProbe, build_health_router
from open_notebook.entrypoints.api.observability import install_observability


def create_app(database: AvailabilityProbe, version: str) -> FastAPI:
    app = FastAPI(
        title="Open Notebook API",
        version=version,
        openapi_url="/api/openapi.json",
        docs_url="/api/docs",
        redoc_url=None,
    )
    install_observability(app)
    app.include_router(build_health_router(database, version))
    return app
