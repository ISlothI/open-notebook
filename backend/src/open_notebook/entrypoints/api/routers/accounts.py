from fastapi import APIRouter, Request, Response, status

from open_notebook.entrypoints.api.schemas import Credentials, UserBody
from open_notebook.entrypoints.api.session import (
    SESSION_COOKIE,
    CurrentServices,
    CurrentUser,
    clear_session_cookie,
    set_session_cookie,
)

router = APIRouter(prefix="/api/auth", tags=["accounts"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(body: Credentials, response: Response, services: CurrentServices) -> UserBody:
    signed_in = services.accounts.register(body.email, body.password)
    set_session_cookie(response, signed_in.token)
    return UserBody.of(signed_in.user)


@router.post("/sign-in")
def sign_in(
    body: Credentials, request: Request, response: Response, services: CurrentServices
) -> UserBody:
    client = request.client.host if request.client else "unknown"
    signed_in = services.accounts.sign_in(body.email, body.password, client)
    set_session_cookie(response, signed_in.token)
    return UserBody.of(signed_in.user)


@router.post("/sign-out", status_code=status.HTTP_204_NO_CONTENT)
def sign_out(request: Request, response: Response, services: CurrentServices) -> None:
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        services.accounts.sign_out(token)
    clear_session_cookie(response)


@router.get("/me")
def me(user: CurrentUser) -> UserBody:
    return UserBody.of(user)
