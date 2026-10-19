from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

import httpx
from sqlalchemy import or_, select

from app.core.config import get_settings
from app.db.models import CheckResult, Monitor
from app.db.session import SessionLocal
from app.services.validators import ValidationOutcome, validate_http_payload
from app.templates import get_target_template

logger = logging.getLogger("cloudpulse.monitor")


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


def _safe_error(reason_code: str, summary: str, *, latency_ms: int | None = None) -> ProbeResult:
    return ProbeResult(
        checked_at=datetime.now(UTC),
        status="DOWN",
        latency_ms=latency_ms,
        reason_code=reason_code,
        error_summary=summary[:500],
    )


def _validate_approved_url(monitor: Monitor) -> bool:
    settings = get_settings()
    try:
        template = get_target_template(monitor.target_key)
    except ValueError:
        return False
    return monitor.url == template.resolved_url(settings)


async def probe_monitor(monitor: Monitor, client: httpx.AsyncClient) -> ProbeResult:
    settings = get_settings()
    if not _validate_approved_url(monitor):
        return _safe_error("TARGET_NOT_APPROVED", "The configured URL does not match its approved template.")

    started = time.perf_counter()
    try:
        async with asyncio.timeout(settings.request_timeout_seconds):
            async with client.stream(
                "GET",
                monitor.url,
                headers={"Accept": "application/json", "User-Agent": "CloudPulse/1.1 health-monitor"},
            ) as response:
                body = bytearray()
                async for chunk in response.aiter_bytes():
                    body.extend(chunk)
                    if len(body) > settings.max_response_bytes:
                        latency_ms = round((time.perf_counter() - started) * 1000)
                        return ProbeResult(
                            checked_at=datetime.now(UTC),
                            status="DOWN",
                            http_status=response.status_code,
                            latency_ms=latency_ms,
                            reason_code="RESPONSE_TOO_LARGE",
                            error_summary="The response exceeded the configured size limit.",
                        )
                latency_ms = round((time.perf_counter() - started) * 1000)
                outcome: ValidationOutcome = validate_http_payload(
                    profile=monitor.validation_profile,
                    expected_status=monitor.expected_status,
                    http_status=response.status_code,
                    content_type=response.headers.get("content-type", ""),
                    body=bytes(body),
                    latency_ms=latency_ms,
                    max_latency_ms=monitor.max_latency_ms,
                    stale_after_days=settings.frankfurter_stale_after_days,
                    today=datetime.now(UTC).date(),
                )
                return ProbeResult(
                    checked_at=datetime.now(UTC),
                    status=outcome.status,
                    http_status=response.status_code,
                    latency_ms=latency_ms,
                    reason_code=outcome.reason_code,
                    error_summary=outcome.error_summary,
                    source_data_date=outcome.source_data_date,
                    data_warning=outcome.data_warning,
                )
    except (TimeoutError, httpx.TimeoutException):
        latency_ms = round((time.perf_counter() - started) * 1000)
        return _safe_error("TIMEOUT", "The target did not respond before the timeout.", latency_ms=latency_ms)
    except httpx.RequestError:
        latency_ms = round((time.perf_counter() - started) * 1000)
        return _safe_error("CONNECTION_ERROR", "The target connection failed.", latency_ms=latency_ms)


def claim_due_monitors(execution_id: str) -> list[Monitor]:
    settings = get_settings()
    now = datetime.now(UTC)
    with SessionLocal.begin() as db:
        monitors = list(
            db.scalars(
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
        )
        for monitor in monitors:
            monitor.claimed_execution_id = execution_id
            monitor.lease_expires_at = now + timedelta(seconds=settings.monitor_lease_seconds)
        return monitors


def save_probe_result(execution_id: str, monitor_id, result: ProbeResult) -> bool:
    with SessionLocal.begin() as db:
        monitor = db.scalar(select(Monitor).where(Monitor.id == monitor_id).with_for_update())
        if monitor is None or monitor.claimed_execution_id != execution_id:
            logger.warning("Discarding result for an expired claim", extra={"monitor_id": str(monitor_id)})
            return False
        db.add(
            CheckResult(
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
        )
        monitor.last_checked_at = result.checked_at
        if monitor.source_kind == "REAL" and result.reason_code == "RATE_LIMITED":
            monitor.rate_limit_streak += 1
            delay_minutes = min(60 * (2**monitor.rate_limit_streak), 24 * 60)
        else:
            monitor.rate_limit_streak = 0
            delay_minutes = monitor.check_interval_minutes
        monitor.next_check_at = result.checked_at + timedelta(minutes=delay_minutes)
        monitor.lease_expires_at = None
        monitor.claimed_execution_id = None
        db.flush()
        return True


async def execute_due_monitors(execution_id: str | None = None) -> dict[str, int | str]:
    settings = get_settings()
    current_execution_id = execution_id or str(uuid.uuid4())
    monitors = claim_due_monitors(current_execution_id)
    semaphore = asyncio.Semaphore(settings.max_monitor_concurrency)
    timeout = httpx.Timeout(settings.request_timeout_seconds)

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
        async def run_one(monitor: Monitor) -> tuple[Monitor, ProbeResult]:
            async with semaphore:
                return monitor, await probe_monitor(monitor, client)

        results = await asyncio.gather(*(run_one(monitor) for monitor in monitors))

    saved = 0
    failed = 0
    for monitor, result in results:
        if save_probe_result(current_execution_id, monitor.id, result):
            saved += 1
        if result.status == "DOWN":
            failed += 1
    summary: dict[str, int | str] = {
        "execution_id": current_execution_id,
        "claimed": len(monitors),
        "saved": saved,
        "down": failed,
    }
    logger.info("Monitor execution completed", extra=summary)
    return summary

