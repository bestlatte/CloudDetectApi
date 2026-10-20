from __future__ import annotations

import uuid
from collections.abc import Iterable
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import CheckResult, Monitor


class CheckRepository:
    """Persistence and read-model queries for monitor check results."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_latest_for_monitor(self, monitor_id: uuid.UUID) -> CheckResult | None:
        statement = (
            select(CheckResult)
            .where(CheckResult.monitor_id == monitor_id)
            .order_by(
                CheckResult.checked_at.desc(),
                CheckResult.created_at.desc(),
                CheckResult.id.desc(),
            )
            .limit(1)
        )
        return self.session.scalar(statement)

    def get_latest_by_monitor_ids(
        self,
        monitor_ids: Iterable[uuid.UUID],
    ) -> dict[uuid.UUID, CheckResult]:
        ids = tuple(monitor_ids)
        if not ids:
            return {}

        ranked_checks = (
            select(
                CheckResult.id.label("check_id"),
                CheckResult.monitor_id.label("monitor_id"),
                func.row_number()
                .over(
                    partition_by=CheckResult.monitor_id,
                    order_by=(
                        CheckResult.checked_at.desc(),
                        CheckResult.created_at.desc(),
                        CheckResult.id.desc(),
                    ),
                )
                .label("row_number"),
            )
            .where(CheckResult.monitor_id.in_(ids))
            .subquery()
        )
        statement = (
            select(CheckResult)
            .join(ranked_checks, ranked_checks.c.check_id == CheckResult.id)
            .where(ranked_checks.c.row_number == 1)
        )
        checks = self.session.scalars(statement)
        return {check.monitor_id: check for check in checks}

    def list_history(
        self,
        *,
        monitor_id: uuid.UUID | None = None,
        source_kind: str | None = None,
        limit: int = 50,
        include_deleted_monitors: bool = False,
    ) -> list[tuple[CheckResult, Monitor]]:
        statement = (
            select(CheckResult, Monitor)
            .join(Monitor, Monitor.id == CheckResult.monitor_id)
            .order_by(
                CheckResult.checked_at.desc(),
                CheckResult.created_at.desc(),
                CheckResult.id.desc(),
            )
            .limit(limit)
        )
        if not include_deleted_monitors:
            statement = statement.where(Monitor.deleted_at.is_(None))
        if monitor_id is not None:
            statement = statement.where(CheckResult.monitor_id == monitor_id)
        if source_kind is not None:
            statement = statement.where(Monitor.source_kind == source_kind)

        return [(check, monitor) for check, monitor in self.session.execute(statement)]

    def get_last_checked_at(self) -> datetime | None:
        return self.session.scalar(select(func.max(CheckResult.checked_at)))

    def get_by_execution_monitor(
        self,
        execution_id: str,
        monitor_id: uuid.UUID,
    ) -> CheckResult | None:
        statement = select(CheckResult).where(
            CheckResult.execution_id == execution_id,
            CheckResult.monitor_id == monitor_id,
        )
        return self.session.scalar(statement)

    def exists_for_execution(self, execution_id: str, monitor_id: uuid.UUID) -> bool:
        statement = select(CheckResult.id).where(
            CheckResult.execution_id == execution_id,
            CheckResult.monitor_id == monitor_id,
        )
        return self.session.scalar(statement) is not None

    def add(self, check: CheckResult) -> CheckResult:
        self.session.add(check)
        self.session.flush()
        return check

    def flush(self) -> None:
        self.session.flush()

    def refresh(self, check: CheckResult) -> CheckResult:
        self.session.refresh(check)
        return check
