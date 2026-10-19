from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select

from app.core.config import get_settings
from app.db.models import Monitor
from app.db.session import SessionLocal
from app.templates import TARGET_TEMPLATES

SEED_NAMESPACE = uuid.UUID("96d1e64a-9fdb-4c14-a07c-067b15a33a89")


def seed_monitors() -> int:
    settings = get_settings()
    created = 0
    with SessionLocal.begin() as db:
        for template in TARGET_TEMPLATES.values():
            existing = db.scalar(select(Monitor).where(Monitor.target_key == template.key))
            if existing:
                continue
            db.add(
                Monitor(
                    id=uuid.uuid5(SEED_NAMESPACE, template.key),
                    target_key=template.key,
                    name=template.default_name,
                    url=template.resolved_url(settings),
                    source_kind=template.source_kind,
                    expected_status=template.expected_status,
                    max_latency_ms=template.max_latency_ms,
                    check_interval_minutes=template.check_interval_minutes,
                    validation_profile=template.validation_profile,
                    enabled=True,
                    next_check_at=datetime.now(UTC),
                )
            )
            created += 1
    return created


if __name__ == "__main__":
    print({"created": seed_monitors()})

