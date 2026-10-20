from __future__ import annotations

from app.repositories.check_repository import CheckRepository
from app.repositories.monitor_repository import MonitorRepository
from app.schemas import OverviewRead, StatusCounts


class OverviewService:
    """Build the dashboard overview without exposing persistence records."""

    def __init__(self, monitors: MonitorRepository, checks: CheckRepository) -> None:
        self._monitors = monitors
        self._checks = checks

    def get_overview(self) -> OverviewRead:
        monitors = self._monitors.list_active(include_disabled=False)
        latest_checks = self._checks.get_latest_by_monitor_ids(monitor.id for monitor in monitors)
        counts = {"REAL": StatusCounts(), "MOCK": StatusCounts()}

        for monitor in monitors:
            latest_check = latest_checks.get(monitor.id)
            status_key = (latest_check.status if latest_check else "UNKNOWN").lower()
            source_counts = counts[monitor.source_kind]
            setattr(source_counts, status_key, getattr(source_counts, status_key) + 1)

        return OverviewRead(
            total_targets=len(monitors),
            real=counts["REAL"],
            mock=counts["MOCK"],
            last_job_at=self._checks.get_last_checked_at(),
        )
