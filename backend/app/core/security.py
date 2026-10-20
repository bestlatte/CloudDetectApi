from __future__ import annotations

from fastapi import HTTPException, Request, status

from app.core.config import get_settings
from app.dependencies import AuthServiceDependency
from app.services.auth_service import AdminSessionInfo


def validate_origin(request: Request) -> None:
    """Validate the browser Origin at the HTTP boundary."""

    origin = request.headers.get("origin", "").rstrip("/")
    if origin not in get_settings().origin_list:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Origin is not allowed.")


def get_optional_admin_session(
    request: Request,
    service: AuthServiceDependency,
) -> AdminSessionInfo | None:
    token = request.cookies.get(get_settings().cookie_name)
    return service.get_optional_session(token)


def require_admin_session(
    request: Request,
    service: AuthServiceDependency,
) -> AdminSessionInfo:
    token = request.cookies.get(get_settings().cookie_name)
    return service.require_session(token)


def require_admin_write(
    request: Request,
    service: AuthServiceDependency,
) -> AdminSessionInfo:
    settings = get_settings()
    admin_session = service.require_session(request.cookies.get(settings.cookie_name))
    validate_origin(request)
    service.validate_csrf(
        admin_session,
        header_token=request.headers.get("x-csrf-token"),
        cookie_token=request.cookies.get(settings.csrf_cookie_name),
    )
    return admin_session
