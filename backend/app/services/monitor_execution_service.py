from __future__ import annotations

import logging
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from app.db.models import Monitor
from app.repositories.monitor_execution_repository import MonitorExecutionRepository

logger = logging.getLogger("cloudpulse.monitor")

SCHEDULER_TICK_MINUTES = 5
NowProvider = Callable[[], datetime]


def _utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True)
class ProbeResult:
    checked_at: datetime
    status: str
    http_status: int | None = None
    latency_ms: int | None = None
    reason_code: str | None = None
    error_summary: str | None = None
    source_data_date: date | None = None
    data_warning: str | None = None


def next_mock_check_at(checked_at: datetime, interval_minutes: int) -> datetime:
    """Keep Mock checks on the five-minute Cloud Scheduler cadence."""

    checked_at_utc = checked_at.replace(tzinfo=UTC) if checked_at.tzinfo is None else checked_at.astimezone(UTC)
    current_tick = checked_at_utc.replace(second=0, microsecond=0) - timedelta(
        minutes=checked_at_utc.minute % SCHEDULER_TICK_MINUTES
    )
    return current_tick + timedelta(minutes=interval_minutes)


class MonitorExecutionService:
    """Business rules for claiming targets and persisting probe results.

    The caller owns the transaction. A claim and a result save are intentionally
    performed in separate short transactions so no database lock is held while
    an external HTTP request is in flight.
    """

    def __init__(
        self,
        executions: MonitorExecutionRepository,
        *,
        lease_seconds: int,
        now: NowProvider = _utc_now,
    ) -> None:
        self._executions = executions
        self._lease_seconds = lease_seconds
        self._now = now

    def claim_due_monitors(self, execution_id: str) -> list[Monitor]:
        now = self._now()
        return self._executions.claim_due(
            execution_id=execution_id,
            now=now,
            lease_expires_at=now + timedelta(seconds=self._lease_seconds),
        )

    def save_probe_result(
        self,
        execution_id: str,
        monitor_id: uuid.UUID,
        result: ProbeResult,
    ) -> bool:
        monitor = self._executions.get_claimed_for_update(monitor_id, execution_id)
        if monitor is None:
            logger.warning(
                "Discarding result for an expired claim",
                extra={"monitor_id": str(monitor_id)},
            )
            return False

        self._executions.create_check(
            monitor_id=monitor.id,
            checked_at=result.checked_at,
            status=result.status,
            http_status=result.http_status,
            latency_ms=result.latency_ms,
            reason_code=result.reason_code,
            error_summary=result.error_summary,
            source_data_date=result.source_data_date,
            data_warning=result.data_warning,
            execution_id=execution_id,
        )
        monitor.last_checked_at = result.checked_at

        if monitor.source_kind == "REAL" and result.reason_code == "RATE_LIMITED":
            monitor.rate_limit_streak += 1
            delay_minutes = min(60 * (2**monitor.rate_limit_streak), 24 * 60)
        else:
            monitor.rate_limit_streak = 0
            delay_minutes = monitor.check_interval_minutes

        if monitor.source_kind == "MOCK":
            monitor.next_check_at = next_mock_check_at(result.checked_at, delay_minutes)
        else:
            monitor.next_check_at = result.checked_at + timedelta(minutes=delay_minutes)

        monitor.lease_expires_at = None
        monitor.claimed_execution_id = None
        self._executions.flush()
        return True
