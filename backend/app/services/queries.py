from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import CheckResult, Monitor
from app.schemas import CheckRead, MonitorRead


def latest_check(db: Session, monitor_id) -> CheckResult | None:
    return db.scalar(
        select(CheckResult)
        .where(CheckResult.monitor_id == monitor_id)
        .order_by(CheckResult.checked_at.desc())
        .limit(1)
    )


def monitor_to_read(db: Session, monitor: Monitor) -> MonitorRead:
    check = latest_check(db, monitor.id)
    return MonitorRead(
        id=monitor.id,
        target_key=monitor.target_key,
        name=monitor.name,
        url=monitor.url,
        source_kind=monitor.source_kind,
        expected_status=monitor.expected_status,
        max_latency_ms=monitor.max_latency_ms,
        check_interval_minutes=monitor.check_interval_minutes,
        validation_profile=monitor.validation_profile,
        enabled=monitor.enabled,
        last_checked_at=monitor.last_checked_at,
        next_check_at=monitor.next_check_at,
        latest_status=check.status if check else "UNKNOWN",
        latest_http_status=check.http_status if check else None,
        latest_latency_ms=check.latency_ms if check else None,
        latest_reason_code=check.reason_code if check else None,
        latest_data_warning=check.data_warning if check else None,
        source_data_date=check.source_data_date if check else None,
    )


def check_to_read(check: CheckResult, monitor: Monitor) -> CheckRead:
    return CheckRead(
        id=check.id,
        monitor_id=check.monitor_id,
        monitor_name=monitor.name,
        source_kind=monitor.source_kind,
        checked_at=check.checked_at,
        status=check.status,
        http_status=check.http_status,
        latency_ms=check.latency_ms,
        reason_code=check.reason_code,
        error_summary=check.error_summary,
        source_data_date=check.source_data_date,
        data_warning=check.data_warning,
        execution_id=check.execution_id,
    )

