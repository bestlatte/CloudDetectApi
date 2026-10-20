from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response, status

from app.core.config import get_settings
from app.core.security import require_admin_write, validate_origin
from app.dependencies import AuthServiceDependency
from app.schemas import LoginRequest, SessionRead

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])


@router.post("/login", response_model=SessionRead)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    service: AuthServiceDependency,
) -> SessionRead:
    validate_origin(request)
    client_key = request.client.host if request.client else "unknown"
    result = service.login(payload.password, client_key)
    settings = get_settings()
    cookie_options = {
        "secure": settings.secure_cookies,
        "samesite": "strict",
        "path": "/",
        "max_age": settings.session_ttl_hours * 3600,
    }
    response.set_cookie(settings.cookie_name, result.raw_token, httponly=True, **cookie_options)
    response.set_cookie(settings.csrf_cookie_name, result.raw_csrf, httponly=False, **cookie_options)
    return SessionRead(authenticated=True, expires_at=result.expires_at)


@router.get("/session", response_model=SessionRead)
def session_status(request: Request, service: AuthServiceDependency) -> SessionRead:
    settings = get_settings()
    return service.session_status(request.cookies.get(settings.cookie_name))


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin_write)],
)
def logout(
    request: Request,
    response: Response,
    service: AuthServiceDependency,
) -> Response:
    settings = get_settings()
    service.logout(request.cookies.get(settings.cookie_name))
    response.delete_cookie(settings.cookie_name, path="/")
    response.delete_cookie(settings.csrf_cookie_name, path="/")
    response.status_code = status.HTTP_204_NO_CONTENT
    return response
