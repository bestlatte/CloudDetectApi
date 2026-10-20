from __future__ import annotations

import uuid

from app.core.config import get_settings
from app.db.models import Monitor
from app.db.session import SessionLocal
from app.repositories.monitor_execution_repository import MonitorExecutionRepository
from app.services.monitor_execution_service import MonitorExecutionService, ProbeResult


def claim_due_monitors(execution_id: str) -> list[Monitor]:
    """Claim due targets in one short transaction before HTTP probing starts."""

    settings = get_settings()
    with SessionLocal.begin() as db:
        service = MonitorExecutionService(
            MonitorExecutionRepository(db),
            lease_seconds=settings.monitor_lease_seconds,
        )
        return service.claim_due_monitors(execution_id)


def save_probe_result(
    execution_id: str,
    monitor_id: uuid.UUID,
    result: ProbeResult,
) -> bool:
    """Persist one probe result in a transaction separate from the HTTP call."""

    settings = get_settings()
    with SessionLocal.begin() as db:
        service = MonitorExecutionService(
            MonitorExecutionRepository(db),
            lease_seconds=settings.monitor_lease_seconds,
        )
        return service.save_probe_result(execution_id, monitor_id, result)
