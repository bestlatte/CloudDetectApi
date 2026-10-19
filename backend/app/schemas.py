from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SourceKind = Literal["REAL", "MOCK"]
HealthStatus = Literal["UP", "DOWN", "DEGRADED", "UNKNOWN"]


class MonitorCreate(BaseModel):
    target_key: str = Field(min_length=1, max_length=64)
    name: str | None = Field(default=None, min_length=1, max_length=120)
    expected_status: int | None = Field(default=None, ge=100, le=599)
    max_latency_ms: int | None = Field(default=None, ge=100, le=30000)
    check_interval_minutes: int | None = Field(default=None, ge=5, le=10080)


class MonitorUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    expected_status: int | None = Field(default=None, ge=100, le=599)
    max_latency_ms: int | None = Field(default=None, ge=100, le=30000)
    check_interval_minutes: int | None = Field(default=None, ge=5, le=10080)
    enabled: bool | None = None


class MonitorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    target_key: str
    name: str
    url: str
    source_kind: SourceKind
    expected_status: int
    max_latency_ms: int
    check_interval_minutes: int
    validation_profile: str
    enabled: bool
    last_checked_at: datetime | None
    next_check_at: datetime | None
    latest_status: HealthStatus = "UNKNOWN"
    latest_http_status: int | None = None
    latest_latency_ms: int | None = None
    latest_reason_code: str | None = None
    latest_data_warning: str | None = None
    source_data_date: date | None = None


class CheckRead(BaseModel):
    id: uuid.UUID
    monitor_id: uuid.UUID
    monitor_name: str
    source_kind: SourceKind
    checked_at: datetime
    status: Literal["UP", "DOWN", "DEGRADED"]
    http_status: int | None
    latency_ms: int | None
    reason_code: str | None
    error_summary: str | None
    source_data_date: date | None
    data_warning: str | None
    execution_id: str


class StatusCounts(BaseModel):
    up: int = 0
    down: int = 0
    degraded: int = 0
    unknown: int = 0


class OverviewRead(BaseModel):
    total_targets: int
    real: StatusCounts
    mock: StatusCounts
    last_job_at: datetime | None


class LoginRequest(BaseModel):
    password: str = Field(min_length=1, max_length=256)


class SessionRead(BaseModel):
    authenticated: bool
    expires_at: datetime | None = None

