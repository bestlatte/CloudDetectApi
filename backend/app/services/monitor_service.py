from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import UTC, datetime

from app.core.config import Settings, get_settings
from app.repositories.check_repository import CheckRepository
from app.repositories.monitor_repository import MonitorRepository
from app.schemas import HealthStatus, MonitorCreate, MonitorRead, MonitorUpdate, SourceKind
from app.services.errors import (
    ApprovedTargetNotFoundError,
    InvalidCheckIntervalError,
    MonitorAlreadyExistsError,
    MonitorNotFoundError,
)
from app.services.mappers import monitor_to_read
from app.templates import TargetTemplate, get_target_template

Commit = Callable[[], None]
NowProvider = Callable[[], datetime]


def _utc_now() -> datetime:
    return datetime.now(UTC)


class MonitorService:
    """Application use cases for monitor configuration and lifecycle."""

    def __init__(
        self,
        monitors: MonitorRepository,
        checks: CheckRepository,
        *,
        commit: Commit,
        settings: Settings | None = None,
        now: NowProvider = _utc_now,
    ) -> None:
        self._monitors = monitors
        self._checks = checks
        self._commit = commit
        self._settings = settings or get_settings()
        self._now = now

    def list_monitors(
        self,
        *,
        source_kind: SourceKind | None = None,
        health_status: HealthStatus | None = None,
        include_disabled: bool = False,
    ) -> list[MonitorRead]:
        monitors = self._monitors.list_active(
            source_kind=source_kind,
            include_disabled=include_disabled,
        )
        latest_checks = self._checks.get_latest_by_monitor_ids(monitor.id for monitor in monitors)
        results = [monitor_to_read(monitor, latest_checks.get(monitor.id)) for monitor in monitors]
        if health_status is not None:
            results = [monitor for monitor in results if monitor.latest_status == health_status]
        return results

    def create_monitor(self, payload: MonitorCreate) -> MonitorRead:
        template = self._get_template(payload.target_key)
        interval = payload.check_interval_minutes or template.check_interval_minutes
        self._validate_interval(template.source_kind, interval)

        existing = self._monitors.get_by_target_key(
            template.key,
            include_deleted=True,
            for_update=True,
        )
        if existing is not None and existing.deleted_at is None:
            raise MonitorAlreadyExistsError

        values = {
            "name": payload.name or template.default_name,
            "url": template.resolved_url(self._settings),
            "source_kind": template.source_kind,
            "expected_status": payload.expected_status or template.expected_status,
            "max_latency_ms": payload.max_latency_ms or template.max_latency_ms,
            "check_interval_minutes": interval,
            "validation_profile": template.validation_profile,
            "enabled": True,
            "next_check_at": self._now(),
        }
        if existing is None:
            monitor = self._monitors.create(target_key=template.key, **values)
        else:
            for field, value in values.items():
                setattr(existing, field, value)
            existing.deleted_at = None
            monitor = existing
            self._monitors.flush()

        self._commit()
        self._monitors.refresh(monitor)
        return monitor_to_read(monitor, self._checks.get_latest_for_monitor(monitor.id))

    def update_monitor(self, monitor_id: uuid.UUID, payload: MonitorUpdate) -> MonitorRead:
        monitor = self._monitors.get_by_id(monitor_id, for_update=True)
        if monitor is None:
            raise MonitorNotFoundError

        changes = payload.model_dump(exclude_unset=True)
        if "check_interval_minutes" in changes:
            self._validate_interval(monitor.source_kind, changes["check_interval_minutes"])
        for field, value in changes.items():
            setattr(monitor, field, value)
        if changes.get("enabled") is True and monitor.next_check_at is None:
            monitor.next_check_at = self._now()

        self._monitors.flush()
        self._commit()
        self._monitors.refresh(monitor)
        return monitor_to_read(monitor, self._checks.get_latest_for_monitor(monitor.id))

    def delete_monitor(self, monitor_id: uuid.UUID) -> None:
        monitor = self._monitors.get_by_id(monitor_id, for_update=True)
        if monitor is None:
            raise MonitorNotFoundError

        monitor.enabled = False
        monitor.deleted_at = self._now()
        monitor.lease_expires_at = None
        monitor.claimed_execution_id = None
        self._monitors.flush()
        self._commit()

    @staticmethod
    def _validate_interval(source_kind: str, interval: int) -> None:
        minimum = 60 if source_kind == "REAL" else 5
        if interval < minimum:
            raise InvalidCheckIntervalError(source_kind, minimum)

    @staticmethod
    def _get_template(target_key: str) -> TargetTemplate:
        try:
            return get_target_template(target_key)
        except ValueError as exc:
            raise ApprovedTargetNotFoundError from exc
