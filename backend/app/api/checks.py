from __future__ import annotations

import uuid
from typing import Literal

from fastapi import APIRouter, Query

from app.dependencies import CheckServiceDependency
from app.schemas import CheckRead

router = APIRouter(prefix="/api/v1", tags=["checks"])


@router.get("/checks", response_model=list[CheckRead])
def list_checks(
    service: CheckServiceDependency,
    monitor_id: uuid.UUID | None = None,
    source_kind: Literal["REAL", "MOCK"] | None = None,
    limit: int = Query(default=50, ge=1, le=200),
) -> list[CheckRead]:
    return service.list_checks(
        monitor_id=monitor_id,
        source_kind=source_kind,
        limit=limit,
    )


@router.get("/monitors/{monitor_id}/checks", response_model=list[CheckRead])
def list_monitor_checks(
    monitor_id: uuid.UUID,
    service: CheckServiceDependency,
    limit: int = Query(default=50, ge=1, le=200),
) -> list[CheckRead]:
    return service.list_monitor_checks(monitor_id, limit=limit)
