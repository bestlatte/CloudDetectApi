from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import CheckResult, Monitor
from app.db.session import get_db
from app.schemas import OverviewRead, StatusCounts
from app.services.queries import latest_check

router = APIRouter(prefix="/api/v1", tags=["overview"])


@router.get("/overview", response_model=OverviewRead)
def overview(db: Session = Depends(get_db)) -> OverviewRead:
    monitors = list(db.scalars(select(Monitor).where(Monitor.deleted_at.is_(None), Monitor.enabled.is_(True))))
    counts = {"REAL": StatusCounts(), "MOCK": StatusCounts()}
    for monitor in monitors:
        check = latest_check(db, monitor.id)
        key = (check.status if check else "UNKNOWN").lower()
        setattr(counts[monitor.source_kind], key, getattr(counts[monitor.source_kind], key) + 1)
    last_job_at = db.scalar(select(func.max(CheckResult.checked_at)))
    return OverviewRead(
        total_targets=len(monitors),
        real=counts["REAL"],
        mock=counts["MOCK"],
        last_job_at=last_job_at,
    )

