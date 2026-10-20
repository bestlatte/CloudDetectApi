from __future__ import annotations

from app.db.models import AdminSession, CheckResult, Monitor
from app.schemas import CheckRead, MonitorRead, SessionRead


def monitor_to_read(monitor: Monitor, latest_check: CheckResult | None = None) -> MonitorRead:
    """Map persistence records to the public monitor DTO without issuing queries."""

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
        latest_status=latest_check.status if latest_check else "UNKNOWN",
        latest_http_status=latest_check.http_status if latest_check else None,
        latest_latency_ms=latest_check.latency_ms if latest_check else None,
        latest_reason_code=latest_check.reason_code if latest_check else None,
        latest_data_warning=latest_check.data_warning if latest_check else None,
        source_data_date=latest_check.source_data_date if latest_check else None,
    )


def check_to_read(check: CheckResult, monitor: Monitor) -> CheckRead:
    """Map a check and its monitor to the public history DTO."""

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


def session_to_read(admin_session: AdminSession | None) -> SessionRead:
    """Map an optional server-side session to its public authentication DTO."""

    if admin_session is None:
        return SessionRead(authenticated=False)
    return SessionRead(authenticated=True, expires_at=admin_session.expires_at)
