"""Session cookie, signed-in user and cross-site request protection."""

from collections.abc import Awaitable, Callable
from typing import Annotated
from urllib.parse import urlsplit

from fastapi import Depends, FastAPI, Request, Response, status
from fastapi.responses import JSONResponse

from open_notebook.application.accounts import SESSION_LIFETIME
from open_notebook.application.services import Services
from open_notebook.domain.accounts import User
from open_notebook.entrypoints.api.schemas import ErrorBody

# The prefix makes browsers insist on Secure, Path=/ and no Domain.
SESSION_COOKIE = "__Host-session"
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


def get_services(request: Request) -> Services:
    services: Services = request.app.state.services
    return services


CurrentServices = Annotated[Services, Depends(get_services)]


def get_current_user(request: Request, services: CurrentServices) -> User:
    return services.accounts.authenticate(request.cookies.get(SESSION_COOKIE))


CurrentUser = Annotated[User, Depends(get_current_user)]


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=int(SESSION_LIFETIME.total_seconds()),
        secure=True,
        httponly=True,
        samesite="lax",
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE, secure=True, httponly=True, samesite="lax", path="/")


def is_cross_site(request: Request) -> bool:
    """Browsers attach Origin to every state-changing request."""
    origin = request.headers.get("Origin")
    return origin is not None and urlsplit(origin).netloc != request.headers.get("Host")


def install_cross_site_protection(app: FastAPI) -> None:
    @app.middleware("http")
    async def reject_cross_site(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if request.method not in SAFE_METHODS and is_cross_site(request):
            body = ErrorBody(code="cross_site_request", message="Cross-site request refused.")
            return JSONResponse(
                body.model_dump(exclude_none=True), status_code=status.HTTP_403_FORBIDDEN
            )
        return await call_next(request)
