from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db.models import CheckResult, Monitor


class MonitorExecutionRepository:
    """Atomic persistence operations used by a monitor job execution."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def claim_due(
        self,
        *,
        execution_id: str,
        now: datetime,
        lease_expires_at: datetime,
    ) -> list[Monitor]:
        statement = (
            select(Monitor)
            .where(
                Monitor.enabled.is_(True),
                Monitor.deleted_at.is_(None),
                or_(Monitor.next_check_at.is_(None), Monitor.next_check_at <= now),
                or_(Monitor.lease_expires_at.is_(None), Monitor.lease_expires_at <= now),
            )
            .order_by(Monitor.next_check_at.asc().nullsfirst())
            .with_for_update(skip_locked=True)
        )
        monitors = list(self.session.scalars(statement))
        for monitor in monitors:
            monitor.claimed_execution_id = execution_id
            monitor.lease_expires_at = lease_expires_at
        self.session.flush()
        return monitors

    def get_claimed_for_update(
        self,
        monitor_id: uuid.UUID,
        execution_id: str | None = None,
    ) -> Monitor | None:
        statement = select(Monitor).where(Monitor.id == monitor_id)
        if execution_id is not None:
            statement = statement.where(Monitor.claimed_execution_id == execution_id)
        return self.session.scalar(statement.with_for_update())

    def add_check(self, check: CheckResult) -> CheckResult:
        self.session.add(check)
        self.session.flush()
        return check

    def create_check(
        self,
        *,
        monitor_id: uuid.UUID,
        checked_at: datetime,
        status: str,
        execution_id: str,
        http_status: int | None = None,
        latency_ms: int | None = None,
        reason_code: str | None = None,
        error_summary: str | None = None,
        source_data_date: date | None = None,
        data_warning: str | None = None,
    ) -> CheckResult:
        return self.add_check(
            CheckResult(
                monitor_id=monitor_id,
                checked_at=checked_at,
                status=status,
                http_status=http_status,
                latency_ms=latency_ms,
                reason_code=reason_code,
                error_summary=error_summary,
                source_data_date=source_data_date,
                data_warning=data_warning,
                execution_id=execution_id,
            )
        )

    def flush(self) -> None:
        self.session.flush()

    def refresh(self, monitor: Monitor) -> Monitor:
        self.session.refresh(monitor)
        return monitor
