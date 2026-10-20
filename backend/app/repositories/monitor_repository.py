from __future__ import annotations

import uuid
from collections.abc import Iterable
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Monitor


class MonitorRepository:
    """Persistence operations for monitor configuration records."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_active(
        self,
        *,
        source_kind: str | None = None,
        include_disabled: bool = False,
    ) -> list[Monitor]:
        statement = (
            select(Monitor)
            .where(Monitor.deleted_at.is_(None))
            .order_by(Monitor.source_kind, Monitor.name)
        )
        if source_kind is not None:
            statement = statement.where(Monitor.source_kind == source_kind)
        if not include_disabled:
            statement = statement.where(Monitor.enabled.is_(True))
        return list(self.session.scalars(statement))

    def get_by_id(
        self,
        monitor_id: uuid.UUID,
        *,
        include_deleted: bool = False,
        for_update: bool = False,
    ) -> Monitor | None:
        statement = select(Monitor).where(Monitor.id == monitor_id)
        if not include_deleted:
            statement = statement.where(Monitor.deleted_at.is_(None))
        if for_update:
            statement = statement.with_for_update()
        return self.session.scalar(statement)

    def get_by_target_key(
        self,
        target_key: str,
        *,
        include_deleted: bool = True,
        for_update: bool = False,
    ) -> Monitor | None:
        statement = select(Monitor).where(Monitor.target_key == target_key)
        if not include_deleted:
            statement = statement.where(Monitor.deleted_at.is_(None))
        if for_update:
            statement = statement.with_for_update()
        return self.session.scalar(statement)

    def exists_by_id(self, monitor_id: uuid.UUID, *, include_deleted: bool = False) -> bool:
        statement = select(Monitor.id).where(Monitor.id == monitor_id)
        if not include_deleted:
            statement = statement.where(Monitor.deleted_at.is_(None))
        return self.session.scalar(statement) is not None

    def list_by_target_keys(
        self,
        target_keys: Iterable[str],
        *,
        include_deleted: bool = True,
    ) -> list[Monitor]:
        keys = tuple(target_keys)
        if not keys:
            return []
        statement = select(Monitor).where(Monitor.target_key.in_(keys))
        if not include_deleted:
            statement = statement.where(Monitor.deleted_at.is_(None))
        return list(self.session.scalars(statement))

    def add(self, monitor: Monitor) -> Monitor:
        self.session.add(monitor)
        self.session.flush()
        return monitor

    def create(
        self,
        *,
        target_key: str,
        name: str,
        url: str,
        source_kind: str,
        expected_status: int,
        max_latency_ms: int,
        check_interval_minutes: int,
        validation_profile: str,
        enabled: bool = True,
        next_check_at: datetime | None = None,
        monitor_id: uuid.UUID | None = None,
    ) -> Monitor:
        monitor = Monitor(
            target_key=target_key,
            name=name,
            url=url,
            source_kind=source_kind,
            expected_status=expected_status,
            max_latency_ms=max_latency_ms,
            check_interval_minutes=check_interval_minutes,
            validation_profile=validation_profile,
            enabled=enabled,
            next_check_at=next_check_at,
        )
        if monitor_id is not None:
            monitor.id = monitor_id
        return self.add(monitor)

    def flush(self) -> None:
        self.session.flush()

    def refresh(self, monitor: Monitor) -> Monitor:
        self.session.refresh(monitor)
        return monitor
