from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.services.errors import (
    AdminLoginNotConfiguredError,
    AdminSessionRequiredError,
    ApprovedTargetNotFoundError,
    CsrfValidationError,
    InvalidCheckIntervalError,
    InvalidCredentialsError,
    MonitorAlreadyExistsError,
    MonitorNotFoundError,
    ServiceError,
    TooManyLoginAttemptsError,
)

_STATUS_BY_ERROR: dict[type[ServiceError], int] = {
    ApprovedTargetNotFoundError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    InvalidCheckIntervalError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    MonitorAlreadyExistsError: status.HTTP_409_CONFLICT,
    MonitorNotFoundError: status.HTTP_404_NOT_FOUND,
    AdminLoginNotConfiguredError: status.HTTP_503_SERVICE_UNAVAILABLE,
    InvalidCredentialsError: status.HTTP_401_UNAUTHORIZED,
    TooManyLoginAttemptsError: status.HTTP_429_TOO_MANY_REQUESTS,
    AdminSessionRequiredError: status.HTTP_401_UNAUTHORIZED,
    CsrfValidationError: status.HTTP_403_FORBIDDEN,
}


def register_service_error_handlers(app: FastAPI) -> None:
    """Translate application failures at the HTTP boundary in one place."""

    @app.exception_handler(ServiceError)
    async def handle_service_error(_request: Request, error: ServiceError) -> JSONResponse:
        response_status = _STATUS_BY_ERROR.get(type(error), status.HTTP_500_INTERNAL_SERVER_ERROR)
        return JSONResponse(status_code=response_status, content={"detail": str(error)})
