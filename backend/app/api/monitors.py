from __future__ import annotations

import uuid
from typing import Literal

from fastapi import APIRouter, Depends, status

from app.core.security import require_admin_write
from app.dependencies import MonitorServiceDependency
from app.schemas import MonitorCreate, MonitorRead, MonitorUpdate

router = APIRouter(prefix="/api/v1/monitors", tags=["monitors"])


@router.get("", response_model=list[MonitorRead])
def list_monitors(
    service: MonitorServiceDependency,
    source_kind: Literal["REAL", "MOCK"] | None = None,
    health_status: Literal["UP", "DOWN", "DEGRADED", "UNKNOWN"] | None = None,
    include_disabled: bool = False,
) -> list[MonitorRead]:
    return service.list_monitors(
        source_kind=source_kind,
        health_status=health_status,
        include_disabled=include_disabled,
    )


@router.post(
    "",
    response_model=MonitorRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin_write)],
)
def create_monitor(payload: MonitorCreate, service: MonitorServiceDependency) -> MonitorRead:
    return service.create_monitor(payload)


@router.patch(
    "/{monitor_id}",
    response_model=MonitorRead,
    dependencies=[Depends(require_admin_write)],
)
def update_monitor(
    monitor_id: uuid.UUID,
    payload: MonitorUpdate,
    service: MonitorServiceDependency,
) -> MonitorRead:
    return service.update_monitor(monitor_id, payload)


@router.delete(
    "/{monitor_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin_write)],
)
def delete_monitor(monitor_id: uuid.UUID, service: MonitorServiceDependency) -> None:
    service.delete_monitor(monitor_id)
