from __future__ import annotations

from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models import AdminSession


class AdminSessionRepository:
    """Persistence operations for server-side administrator sessions."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def delete_expired(self, now: datetime) -> int:
        result = self.session.execute(delete(AdminSession).where(AdminSession.expires_at <= now))
        return result.rowcount

    def add(self, admin_session: AdminSession) -> AdminSession:
        self.session.add(admin_session)
        self.session.flush()
        return admin_session

    def create(
        self,
        *,
        token_hash: str,
        csrf_token_hash: str,
        expires_at: datetime,
    ) -> AdminSession:
        return self.add(
            AdminSession(
                token_hash=token_hash,
                csrf_token_hash=csrf_token_hash,
                expires_at=expires_at,
            )
        )

    def get_valid_by_token_hash(self, token_hash: str, *, now: datetime) -> AdminSession | None:
        statement = select(AdminSession).where(
            AdminSession.token_hash == token_hash,
            AdminSession.expires_at > now,
        )
        return self.session.scalar(statement)

    def delete_by_token_hash(self, token_hash: str) -> int:
        result = self.session.execute(delete(AdminSession).where(AdminSession.token_hash == token_hash))
        return result.rowcount

    def flush(self) -> None:
        self.session.flush()

    def refresh(self, admin_session: AdminSession) -> AdminSession:
        self.session.refresh(admin_session)
        return admin_session
