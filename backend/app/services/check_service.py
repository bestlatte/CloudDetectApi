from __future__ import annotations

import uuid

from app.repositories.check_repository import CheckRepository
from app.repositories.monitor_repository import MonitorRepository
from app.schemas import CheckRead, SourceKind
from app.services.errors import MonitorNotFoundError
from app.services.mappers import check_to_read


class CheckService:
    """Application queries for public monitor-check history."""

    def __init__(
        self,
        monitors: MonitorRepository,
        checks: CheckRepository,
    ) -> None:
        self._monitors = monitors
        self._checks = checks

    def list_checks(
        self,
        *,
        monitor_id: uuid.UUID | None = None,
        source_kind: SourceKind | None = None,
        limit: int = 50,
    ) -> list[CheckRead]:
        history = self._checks.list_history(
            monitor_id=monitor_id,
            source_kind=source_kind,
            limit=limit,
        )
        return [check_to_read(check, monitor) for check, monitor in history]

    def list_monitor_checks(self, monitor_id: uuid.UUID, *, limit: int = 50) -> list[CheckRead]:
        if not self._monitors.exists_by_id(monitor_id):
            raise MonitorNotFoundError
        return self.list_checks(monitor_id=monitor_id, limit=limit)
