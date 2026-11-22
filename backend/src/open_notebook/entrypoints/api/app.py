"""Builds the HTTP application from its dependencies."""

from fastapi import FastAPI

from open_notebook.application.services import Services
from open_notebook.entrypoints.api.errors import install_error_handling
from open_notebook.entrypoints.api.health import AvailabilityProbe, build_health_router
from open_notebook.entrypoints.api.observability import install_observability
from open_notebook.entrypoints.api.routers import accounts, library, pages
from open_notebook.entrypoints.api.session import install_cross_site_protection


def create_app(database: AvailabilityProbe, services: Services, version: str) -> FastAPI:
    app = FastAPI(
        title="Open Notebook API",
        version=version,
        openapi_url="/api/openapi.json",
        docs_url="/api/docs",
        redoc_url=None,
    )
    app.state.services = services
    install_error_handling(app)
    install_cross_site_protection(app)
    # Installed last, so that it wraps everything else.
    install_observability(app)
    app.include_router(build_health_router(database, version))
    app.include_router(accounts.router)
    app.include_router(library.router)
    app.include_router(pages.router)
    return app
