"""Translates business rule violations to HTTP responses."""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from open_notebook.domain import errors
from open_notebook.domain.pages import VersionConflictError
from open_notebook.entrypoints.api.schemas import ErrorBody, PageBody

STATUS_BY_ERROR: dict[type[errors.DomainError], int] = {
    errors.NotFoundError: status.HTTP_404_NOT_FOUND,
    errors.InvalidValueError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    errors.InvalidHierarchyError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    errors.ParentTrashedError: status.HTTP_409_CONFLICT,
    errors.EmailTakenError: status.HTTP_409_CONFLICT,
    VersionConflictError: status.HTTP_409_CONFLICT,
    errors.InvalidCredentialsError: status.HTTP_401_UNAUTHORIZED,
    errors.NotSignedInError: status.HTTP_401_UNAUTHORIZED,
    errors.TooManyAttemptsError: status.HTTP_429_TOO_MANY_REQUESTS,
}


def install_error_handling(app: FastAPI) -> None:
    @app.exception_handler(errors.DomainError)
    def handle(_request: Request, error: errors.DomainError) -> JSONResponse:
        body = ErrorBody(code=error.code, message=error.message)
        if isinstance(error, VersionConflictError):
            body.current = PageBody.of(error.current)
        return JSONResponse(
            body.model_dump(mode="json", exclude_none=True),
            status_code=STATUS_BY_ERROR.get(type(error), status.HTTP_400_BAD_REQUEST),
        )
