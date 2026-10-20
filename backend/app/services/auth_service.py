from __future__ import annotations

import hashlib
import secrets
import uuid
from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hmac import compare_digest
from threading import Lock

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from app.core.config import Settings, get_settings
from app.repositories.admin_session_repository import AdminSessionRepository
from app.schemas import SessionRead
from app.services.errors import (
    AdminLoginNotConfiguredError,
    AdminSessionRequiredError,
    CsrfValidationError,
    InvalidCredentialsError,
    TooManyLoginAttemptsError,
)

Commit = Callable[[], None]
NowProvider = Callable[[], datetime]


def _utc_now() -> datetime:
    return datetime.now(UTC)


def hash_token(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class LoginResult:
    raw_token: str
    raw_csrf: str
    expires_at: datetime


@dataclass(frozen=True)
class AdminSessionInfo:
    id: uuid.UUID
    token_hash: str
    csrf_token_hash: str
    expires_at: datetime


class LoginAttemptLimiter:
    """Process-local login limiter matching the v1 controller behaviour."""

    def __init__(self, *, maximum_attempts: int = 5, window: timedelta = timedelta(minutes=15)) -> None:
        self._maximum_attempts = maximum_attempts
        self._window = window
        self._attempts: dict[str, deque[datetime]] = defaultdict(deque)
        self._lock = Lock()

    def check_and_record(self, client_key: str, now: datetime) -> None:
        cutoff = now - self._window
        with self._lock:
            attempts = self._attempts[client_key]
            while attempts and attempts[0] < cutoff:
                attempts.popleft()
            if len(attempts) >= self._maximum_attempts:
                raise TooManyLoginAttemptsError
            attempts.append(now)

    def clear(self, client_key: str) -> None:
        with self._lock:
            self._attempts.pop(client_key, None)


_login_attempt_limiter = LoginAttemptLimiter()


class AuthService:
    """Authenticate administrators and manage their server-side sessions."""

    def __init__(
        self,
        sessions: AdminSessionRepository,
        *,
        commit: Commit,
        settings: Settings | None = None,
        limiter: LoginAttemptLimiter = _login_attempt_limiter,
        now: NowProvider = _utc_now,
        password_hasher: PasswordHasher | None = None,
    ) -> None:
        self._sessions = sessions
        self._commit = commit
        self._settings = settings or get_settings()
        self._limiter = limiter
        self._now = now
        self._password_hasher = password_hasher or PasswordHasher()

    def login(self, password: str, client_key: str) -> LoginResult:
        if not self._settings.admin_password_hash:
            raise AdminLoginNotConfiguredError

        now = self._now()
        self._limiter.check_and_record(client_key, now)
        if not self._verify_password(password):
            raise InvalidCredentialsError
        self._limiter.clear(client_key)

        self._sessions.delete_expired(now)
        raw_token = secrets.token_urlsafe(48)
        raw_csrf = secrets.token_urlsafe(32)
        expires_at = now + timedelta(hours=self._settings.session_ttl_hours)
        admin_session = self._sessions.create(
            token_hash=hash_token(raw_token),
            csrf_token_hash=hash_token(raw_csrf),
            expires_at=expires_at,
        )
        self._commit()
        self._sessions.refresh(admin_session)
        return LoginResult(raw_token=raw_token, raw_csrf=raw_csrf, expires_at=admin_session.expires_at)

    def get_optional_session(self, raw_token: str | None) -> AdminSessionInfo | None:
        if not raw_token:
            return None
        admin_session = self._sessions.get_valid_by_token_hash(
            hash_token(raw_token),
            now=self._now(),
        )
        if admin_session is None:
            return None
        return AdminSessionInfo(
            id=admin_session.id,
            token_hash=admin_session.token_hash,
            csrf_token_hash=admin_session.csrf_token_hash,
            expires_at=admin_session.expires_at,
        )

    def require_session(self, raw_token: str | None) -> AdminSessionInfo:
        admin_session = self.get_optional_session(raw_token)
        if admin_session is None:
            raise AdminSessionRequiredError
        return admin_session

    def session_status(self, raw_token: str | None) -> SessionRead:
        admin_session = self.get_optional_session(raw_token)
        if admin_session is None:
            return SessionRead(authenticated=False)
        return SessionRead(authenticated=True, expires_at=admin_session.expires_at)

    def validate_csrf(
        self,
        admin_session: AdminSessionInfo,
        *,
        header_token: str | None,
        cookie_token: str | None,
    ) -> None:
        header = header_token or ""
        cookie = cookie_token or ""
        if not header or not cookie or not compare_digest(header, cookie):
            raise CsrfValidationError
        if not compare_digest(hash_token(header), admin_session.csrf_token_hash):
            raise CsrfValidationError

    def logout(self, raw_token: str | None) -> None:
        if not raw_token:
            return
        self._sessions.delete_by_token_hash(hash_token(raw_token))
        self._commit()

    def _verify_password(self, password: str) -> bool:
        try:
            return self._password_hasher.verify(self._settings.admin_password_hash, password)
        except (VerifyMismatchError, InvalidHashError):
            return False
