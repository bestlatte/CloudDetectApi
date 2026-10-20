from __future__ import annotations

import asyncio
import logging
import time
import uuid
from collections.abc import Callable
from datetime import UTC, datetime

import httpx

from app.core.config import get_settings
from app.db.models import Monitor
from app.services.monitor_execution_service import (
    ProbeResult,
    next_mock_check_at,
)
from app.services.validators import ValidationOutcome, validate_http_payload
from app.templates import get_target_template

logger = logging.getLogger("cloudpulse.monitor")

ClaimDueMonitors = Callable[[str], list[Monitor]]
SaveProbeResult = Callable[[str, uuid.UUID, ProbeResult], bool]


def _next_mock_check_at(checked_at: datetime, interval_minutes: int) -> datetime:
    """Backward-compatible public helper for scheduler-aligned Mock checks."""

    return next_mock_check_at(checked_at, interval_minutes)


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


async def execute_due_monitors(
    execution_id: str | None = None,
    *,
    claim_due: ClaimDueMonitors,
    save_result: SaveProbeResult,
) -> dict[str, int | str]:
    settings = get_settings()
    current_execution_id = execution_id or str(uuid.uuid4())
    monitors = claim_due(current_execution_id)
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
        if save_result(current_execution_id, monitor.id, result):
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

