from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import require_admin_write
from app.db.models import Monitor
from app.db.session import get_db
from app.schemas import MonitorCreate, MonitorRead, MonitorUpdate
from app.services.queries import monitor_to_read
from app.templates import get_target_template

router = APIRouter(prefix="/api/v1/monitors", tags=["monitors"])


def _validate_interval(source_kind: str, interval: int) -> None:
    minimum = 60 if source_kind == "REAL" else 5
    if interval < minimum:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"{source_kind} targets require an interval of at least {minimum} minutes.",
        )


@router.get("", response_model=list[MonitorRead])
def list_monitors(
    source_kind: Literal["REAL", "MOCK"] | None = None,
    health_status: Literal["UP", "DOWN", "DEGRADED", "UNKNOWN"] | None = None,
    include_disabled: bool = False,
    db: Session = Depends(get_db),
) -> list[MonitorRead]:
    query = select(Monitor).where(Monitor.deleted_at.is_(None)).order_by(Monitor.source_kind, Monitor.name)
    if source_kind:
        query = query.where(Monitor.source_kind == source_kind)
    if not include_disabled:
        query = query.where(Monitor.enabled.is_(True))
    monitors = [monitor_to_read(db, item) for item in db.scalars(query)]
    if health_status:
        monitors = [item for item in monitors if item.latest_status == health_status]
    return monitors


@router.post(
    "",
    response_model=MonitorRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin_write)],
)
def create_monitor(payload: MonitorCreate, db: Session = Depends(get_db)) -> MonitorRead:
    try:
        template = get_target_template(payload.target_key)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    interval = payload.check_interval_minutes or template.check_interval_minutes
    _validate_interval(template.source_kind, interval)
    existing = db.scalar(select(Monitor).where(Monitor.target_key == template.key))
    if existing and existing.deleted_at is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This approved target already exists.")
    values = {
        "name": payload.name or template.default_name,
        "url": template.resolved_url(get_settings()),
        "source_kind": template.source_kind,
        "expected_status": payload.expected_status or template.expected_status,
        "max_latency_ms": payload.max_latency_ms or template.max_latency_ms,
        "check_interval_minutes": interval,
        "validation_profile": template.validation_profile,
        "enabled": True,
        "deleted_at": None,
        "next_check_at": datetime.now(UTC),
    }
    if existing:
        for key, value in values.items():
            setattr(existing, key, value)
        monitor = existing
    else:
        monitor = Monitor(target_key=template.key, **values)
        db.add(monitor)
    db.commit()
    db.refresh(monitor)
    return monitor_to_read(db, monitor)


@router.patch("/{monitor_id}", response_model=MonitorRead, dependencies=[Depends(require_admin_write)])
def update_monitor(monitor_id: uuid.UUID, payload: MonitorUpdate, db: Session = Depends(get_db)) -> MonitorRead:
    monitor = db.scalar(select(Monitor).where(Monitor.id == monitor_id, Monitor.deleted_at.is_(None)))
    if monitor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Monitor not found.")
    changes = payload.model_dump(exclude_unset=True)
    if "check_interval_minutes" in changes:
        _validate_interval(monitor.source_kind, changes["check_interval_minutes"])
    for key, value in changes.items():
        setattr(monitor, key, value)
    if changes.get("enabled") is True and monitor.next_check_at is None:
        monitor.next_check_at = datetime.now(UTC)
    db.commit()
    db.refresh(monitor)
    return monitor_to_read(db, monitor)


@router.delete("/{monitor_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_admin_write)])
def delete_monitor(monitor_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    monitor = db.scalar(select(Monitor).where(Monitor.id == monitor_id, Monitor.deleted_at.is_(None)))
    if monitor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Monitor not found.")
    monitor.enabled = False
    monitor.deleted_at = datetime.now(UTC)
    monitor.lease_expires_at = None
    monitor.claimed_execution_id = None
    db.commit()

