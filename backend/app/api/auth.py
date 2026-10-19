from __future__ import annotations

from collections import defaultdict, deque
from datetime import UTC, datetime, timedelta
from threading import Lock

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import (
    create_admin_session,
    get_optional_admin_session,
    hash_token,
    require_admin_write,
    validate_origin,
    verify_admin_password,
)
from app.db.models import AdminSession
from app.db.session import get_db
from app.schemas import LoginRequest, SessionRead

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])
_attempts: dict[str, deque[datetime]] = defaultdict(deque)
_attempt_lock = Lock()


def _check_login_rate(client_key: str) -> None:
    now = datetime.now(UTC)
    cutoff = now - timedelta(minutes=15)
    with _attempt_lock:
        attempts = _attempts[client_key]
        while attempts and attempts[0] < cutoff:
            attempts.popleft()
        if len(attempts) >= 5:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many login attempts.")
        attempts.append(now)


@router.post("/login", response_model=SessionRead)
def login(payload: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)) -> SessionRead:
    settings = get_settings()
    validate_origin(request)
    if not settings.admin_password_hash:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Admin login is not configured.")
    client_key = request.client.host if request.client else "unknown"
    _check_login_rate(client_key)
    if not verify_admin_password(payload.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")
    with _attempt_lock:
        _attempts.pop(client_key, None)
    session, raw_token, raw_csrf = create_admin_session(db)
    cookie_options = {
        "secure": settings.secure_cookies,
        "samesite": "strict",
        "path": "/",
        "max_age": settings.session_ttl_hours * 3600,
    }
    response.set_cookie(settings.cookie_name, raw_token, httponly=True, **cookie_options)
    response.set_cookie(settings.csrf_cookie_name, raw_csrf, httponly=False, **cookie_options)
    return SessionRead(authenticated=True, expires_at=session.expires_at)


@router.get("/session", response_model=SessionRead)
def session_status(request: Request, db: Session = Depends(get_db)) -> SessionRead:
    session = get_optional_admin_session(request, db)
    if session is None:
        return SessionRead(authenticated=False)
    return SessionRead(authenticated=True, expires_at=session.expires_at)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_admin_write)])
def logout(request: Request, response: Response, db: Session = Depends(get_db)) -> Response:
    settings = get_settings()
    raw_token = request.cookies.get(settings.cookie_name)
    if raw_token:
        db.execute(delete(AdminSession).where(AdminSession.token_hash == hash_token(raw_token)))
        db.commit()
    response.delete_cookie(settings.cookie_name, path="/")
    response.delete_cookie(settings.csrf_cookie_name, path="/")
    response.status_code = status.HTTP_204_NO_CONTENT
    return response

