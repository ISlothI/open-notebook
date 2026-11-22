"""Liveness and readiness endpoints."""

from typing import Literal, Protocol

from fastapi import APIRouter, Response, status
from pydantic import BaseModel


class AvailabilityProbe(Protocol):
    def is_available(self) -> bool: ...


class HealthStatus(BaseModel):
    status: Literal["ok", "unavailable"]
    version: str


def build_health_router(database: AvailabilityProbe, version: str) -> APIRouter:
    router = APIRouter(prefix="/api/health", tags=["health"])

    @router.get("/live")
    def live() -> HealthStatus:
        return HealthStatus(status="ok", version=version)

    @router.get("/ready", responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"model": HealthStatus}})
    def ready(response: Response) -> HealthStatus:
        if database.is_available():
            return HealthStatus(status="ok", version=version)
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return HealthStatus(status="unavailable", version=version)

    return router
