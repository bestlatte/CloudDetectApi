from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from app.db.models import CheckResult, Monitor
from app.db.seed import seed_monitors
from app.db.session import SessionLocal
from app.services.monitor_engine import ProbeResult, _next_mock_check_at, claim_due_monitors, save_probe_result


def seconds_between(later: datetime, earlier: datetime) -> int:
    if later.tzinfo is None:
        earlier = earlier.replace(tzinfo=None)
    return round((later - earlier).total_seconds())


def test_seed_is_idempotent_and_creates_eight_targets():
    assert seed_monitors() == 8
    assert seed_monitors() == 0
    with SessionLocal() as db:
        monitors = list(db.scalars(select(Monitor)))
    assert len(monitors) == 8
    real_monitors = [item for item in monitors if item.source_kind == "REAL"]
    assert len(real_monitors) == 4
    assert all(item.check_interval_minutes >= 60 for item in real_monitors)


def test_claim_does_not_take_future_or_leased_targets():
    seed_monitors()
    now = datetime.now(UTC)
    with SessionLocal.begin() as db:
        monitors = list(db.scalars(select(Monitor).order_by(Monitor.target_key)))
        monitors[0].next_check_at = now + timedelta(hours=1)
        monitors[1].lease_expires_at = now + timedelta(minutes=2)
    claimed = claim_due_monitors("execution-one")
    assert len(claimed) == 6
    assert all(item.claimed_execution_id == "execution-one" for item in claimed)
    assert claim_due_monitors("overlapping-execution") == []


def test_expired_lease_is_recovered():
    seed_monitors()
    now = datetime.now(UTC)
    with SessionLocal.begin() as db:
        monitors = list(db.scalars(select(Monitor).order_by(Monitor.target_key)))
        for monitor in monitors:
            monitor.next_check_at = now + timedelta(hours=1)
        monitors[0].next_check_at = now - timedelta(minutes=1)
        monitors[0].lease_expires_at = now - timedelta(seconds=1)
        monitors[0].claimed_execution_id = "abandoned-execution"
        expected_id = monitors[0].id

    claimed = claim_due_monitors("recovery-execution")

    assert [monitor.id for monitor in claimed] == [expected_id]


def test_mock_next_check_is_aligned_to_scheduler_tick():
    seed_monitors()
    execution_id = "mock-schedule-alignment"
    mock = next(
        monitor for monitor in claim_due_monitors(execution_id) if monitor.target_key == "MOCK_HEALTHY"
    )
    checked_at = datetime(2026, 10, 20, 7, 20, 23, tzinfo=UTC)

    assert save_probe_result(
        execution_id,
        mock.id,
        ProbeResult(checked_at=checked_at, status="UP", http_status=200),
    )

    with SessionLocal() as db:
        stored = db.get(Monitor, mock.id)
        assert stored is not None
        expected_next_check = datetime(2026, 10, 20, 7, 25, tzinfo=UTC)
        assert seconds_between(stored.next_check_at, expected_next_check) == 0


def test_mock_schedule_alignment_handles_extended_interval_and_day_boundary():
    checked_at = datetime(2026, 10, 20, 7, 20, 23, tzinfo=UTC)
    assert _next_mock_check_at(checked_at, 10) == datetime(2026, 10, 20, 7, 30, tzinfo=UTC)

    before_midnight = datetime(2026, 10, 20, 23, 58, 12, tzinfo=UTC)
    assert _next_mock_check_at(before_midnight, 5) == datetime(2026, 10, 21, 0, 0, tzinfo=UTC)


def test_rate_limit_backoff_and_successful_recovery():
    seed_monitors()
    first_execution = "rate-limit-one"
    frankfurter = next(
        monitor for monitor in claim_due_monitors(first_execution) if monitor.target_key == "FRANKFURTER_USD_TWD"
    )
    first_checked_at = datetime.now(UTC)
    assert save_probe_result(
        first_execution,
        frankfurter.id,
        ProbeResult(
            checked_at=first_checked_at,
            status="DOWN",
            http_status=429,
            reason_code="RATE_LIMITED",
        ),
    )
    with SessionLocal.begin() as db:
        stored = db.get(Monitor, frankfurter.id)
        assert stored is not None
        assert stored.rate_limit_streak == 1
        assert seconds_between(stored.next_check_at, first_checked_at) == 2 * 60 * 60
        stored.next_check_at = datetime.now(UTC) - timedelta(seconds=1)

    second_execution = "rate-limit-two"
    second = next(
        monitor for monitor in claim_due_monitors(second_execution) if monitor.id == frankfurter.id
    )
    second_checked_at = datetime.now(UTC)
    assert save_probe_result(
        second_execution,
        second.id,
        ProbeResult(
            checked_at=second_checked_at,
            status="DOWN",
            http_status=429,
            reason_code="RATE_LIMITED",
        ),
    )
    with SessionLocal.begin() as db:
        stored = db.get(Monitor, frankfurter.id)
        assert stored is not None
        assert stored.rate_limit_streak == 2
        assert seconds_between(stored.next_check_at, second_checked_at) == 4 * 60 * 60
        stored.next_check_at = datetime.now(UTC) - timedelta(seconds=1)

    recovery_execution = "rate-limit-recovered"
    recovered = next(
        monitor for monitor in claim_due_monitors(recovery_execution) if monitor.id == frankfurter.id
    )
    recovery_checked_at = datetime.now(UTC)
    assert save_probe_result(
        recovery_execution,
        recovered.id,
        ProbeResult(checked_at=recovery_checked_at, status="UP", http_status=200),
    )
    with SessionLocal() as db:
        stored = db.get(Monitor, frankfurter.id)
        assert stored is not None
        assert stored.rate_limit_streak == 0
        assert seconds_between(stored.next_check_at, recovery_checked_at) == 60 * 60


def test_repeated_execution_result_is_idempotent():
    seed_monitors()
    execution_id = "idempotent-execution"
    monitor = claim_due_monitors(execution_id)[0]
    result = ProbeResult(checked_at=datetime.now(UTC), status="UP", http_status=200)

    assert save_probe_result(execution_id, monitor.id, result) is True
    assert save_probe_result(execution_id, monitor.id, result) is False

    with SessionLocal() as db:
        count = db.scalar(
            select(func.count(CheckResult.id)).where(
                CheckResult.execution_id == execution_id,
                CheckResult.monitor_id == monitor.id,
            )
        )
    assert count == 1

