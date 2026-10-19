from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from hmac import compare_digest

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import AdminSession
from app.db.session import get_db

password_hasher = PasswordHasher()


def hash_token(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def verify_admin_password(password: str) -> bool:
    configured_hash = get_settings().admin_password_hash
    if not configured_hash:
        return False
    try:
        return password_hasher.verify(configured_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def create_admin_session(db: Session) -> tuple[AdminSession, str, str]:
    settings = get_settings()
    now = datetime.now(UTC)
    db.execute(delete(AdminSession).where(AdminSession.expires_at <= now))
    raw_token = secrets.token_urlsafe(48)
    raw_csrf = secrets.token_urlsafe(32)
    session = AdminSession(
        token_hash=hash_token(raw_token),
        csrf_token_hash=hash_token(raw_csrf),
        expires_at=now + timedelta(hours=settings.session_ttl_hours),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session, raw_token, raw_csrf


def get_optional_admin_session(request: Request, db: Session) -> AdminSession | None:
    token = request.cookies.get(get_settings().cookie_name)
    if not token:
        return None
    session = db.scalar(
        select(AdminSession).where(
            AdminSession.token_hash == hash_token(token),
            AdminSession.expires_at > datetime.now(UTC),
        )
    )
    return session


def require_admin_session(
    request: Request,
    db: Session = Depends(get_db),
) -> AdminSession:
    session = get_optional_admin_session(request, db)
    if session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Administrator login required.")
    return session


def validate_origin(request: Request) -> None:
    origin = request.headers.get("origin", "").rstrip("/")
    if origin not in get_settings().origin_list:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Origin is not allowed.")


def require_admin_write(
    request: Request,
    session: AdminSession = Depends(require_admin_session),
) -> AdminSession:
    validate_origin(request)
    settings = get_settings()
    header_token = request.headers.get("x-csrf-token", "")
    cookie_token = request.cookies.get(settings.csrf_cookie_name, "")
    if not header_token or not cookie_token or not compare_digest(header_token, cookie_token):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF validation failed.")
    if not compare_digest(hash_token(header_token), session.csrf_token_hash):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF validation failed.")
    return session
