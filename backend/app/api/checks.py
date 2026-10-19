from __future__ import annotations

import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import CheckResult, Monitor
from app.db.session import get_db
from app.schemas import CheckRead
from app.services.queries import check_to_read

router = APIRouter(prefix="/api/v1", tags=["checks"])


def _query_checks(
    db: Session,
    *,
    monitor_id: uuid.UUID | None,
    source_kind: str | None,
    limit: int,
) -> list[CheckRead]:
    query = (
        select(CheckResult, Monitor)
        .join(Monitor, Monitor.id == CheckResult.monitor_id)
        .where(Monitor.deleted_at.is_(None))
        .order_by(CheckResult.checked_at.desc())
        .limit(limit)
    )
    if monitor_id:
        query = query.where(CheckResult.monitor_id == monitor_id)
    if source_kind:
        query = query.where(Monitor.source_kind == source_kind)
    return [check_to_read(check, monitor) for check, monitor in db.execute(query)]


@router.get("/checks", response_model=list[CheckRead])
def list_checks(
    monitor_id: uuid.UUID | None = None,
    source_kind: Literal["REAL", "MOCK"] | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[CheckRead]:
    return _query_checks(db, monitor_id=monitor_id, source_kind=source_kind, limit=limit)


@router.get("/monitors/{monitor_id}/checks", response_model=list[CheckRead])
def list_monitor_checks(
    monitor_id: uuid.UUID,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[CheckRead]:
    exists = db.scalar(select(Monitor.id).where(Monitor.id == monitor_id, Monitor.deleted_at.is_(None)))
    if exists is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Monitor not found.")
    return _query_checks(db, monitor_id=monitor_id, source_kind=None, limit=limit)

