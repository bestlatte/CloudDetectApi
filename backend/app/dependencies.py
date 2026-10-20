from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.repositories.admin_session_repository import AdminSessionRepository
from app.repositories.check_repository import CheckRepository
from app.repositories.monitor_repository import MonitorRepository
from app.services.auth_service import AuthService
from app.services.check_service import CheckService
from app.services.monitor_service import MonitorService
from app.services.overview_service import OverviewService

DatabaseSession = Annotated[Session, Depends(get_db)]


def get_monitor_service(db: DatabaseSession) -> MonitorService:
    """Compose the request-scoped Monitor application service."""

    return MonitorService(
        MonitorRepository(db),
        CheckRepository(db),
        commit=db.commit,
        settings=get_settings(),
    )


def get_check_service(db: DatabaseSession) -> CheckService:
    """Compose the request-scoped Check application service."""

    return CheckService(MonitorRepository(db), CheckRepository(db))


def get_overview_service(db: DatabaseSession) -> OverviewService:
    """Compose the request-scoped dashboard application service."""

    return OverviewService(MonitorRepository(db), CheckRepository(db))


def get_auth_service(db: DatabaseSession) -> AuthService:
    """Compose the request-scoped authentication application service."""

    return AuthService(
        AdminSessionRepository(db),
        commit=db.commit,
        settings=get_settings(),
    )


MonitorServiceDependency = Annotated[MonitorService, Depends(get_monitor_service)]
CheckServiceDependency = Annotated[CheckService, Depends(get_check_service)]
OverviewServiceDependency = Annotated[OverviewService, Depends(get_overview_service)]
AuthServiceDependency = Annotated[AuthService, Depends(get_auth_service)]
