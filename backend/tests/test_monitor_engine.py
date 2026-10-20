import asyncio
import uuid
from datetime import UTC, datetime

import httpx
import pytest

from app.core.config import Settings
from app.db.models import Monitor
from app.services import monitor_engine


@pytest.mark.asyncio
async def test_probe_enforces_total_timeout(monkeypatch):
    settings = Settings(
        environment="test",
        public_base_url="http://backend:8000",
        request_timeout_seconds=0.01,
    )
    monkeypatch.setattr(monitor_engine, "get_settings", lambda: settings)
    monitor = Monitor(
        target_key="MOCK_HEALTHY",
        name="Mock Healthy API",
        url="http://backend:8000/demo/healthy",
        source_kind="MOCK",
        validation_profile="STATUS_SUCCESS",
        expected_status=200,
        max_latency_ms=2000,
        check_interval_minutes=5,
    )

    async def delayed_response(_request: httpx.Request) -> httpx.Response:
        await asyncio.sleep(0.05)
        return httpx.Response(200, json={"status": "success"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(delayed_response)) as client:
        result = await monitor_engine.probe_monitor(monitor, client)

    assert result.status == "DOWN"
    assert result.reason_code == "TIMEOUT"


@pytest.mark.asyncio
async def test_probe_reports_connection_errors(monkeypatch):
    settings = Settings(environment="test", public_base_url="http://backend:8000")
    monkeypatch.setattr(monitor_engine, "get_settings", lambda: settings)
    monitor = Monitor(
        target_key="MOCK_HEALTHY",
        name="Mock Healthy API",
        url="http://backend:8000/demo/healthy",
        source_kind="MOCK",
        validation_profile="STATUS_SUCCESS",
        expected_status=200,
        max_latency_ms=2000,
        check_interval_minutes=5,
    )

    async def connection_failure(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("fixture connection failure", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(connection_failure)) as client:
        result = await monitor_engine.probe_monitor(monitor, client)

    assert result.reason_code == "CONNECTION_ERROR"


@pytest.mark.asyncio
async def test_probe_rejects_oversized_response(monkeypatch):
    settings = Settings(
        environment="test",
        public_base_url="http://backend:8000",
        max_response_bytes=8,
    )
    monkeypatch.setattr(monitor_engine, "get_settings", lambda: settings)
    monitor = Monitor(
        target_key="MOCK_HEALTHY",
        name="Mock Healthy API",
        url="http://backend:8000/demo/healthy",
        source_kind="MOCK",
        validation_profile="STATUS_SUCCESS",
        expected_status=200,
        max_latency_ms=2000,
        check_interval_minutes=5,
    )

    async def large_response(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b'{"status":"success"}', headers={"content-type": "application/json"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(large_response)) as client:
        result = await monitor_engine.probe_monitor(monitor, client)

    assert result.reason_code == "RESPONSE_TOO_LARGE"


@pytest.mark.asyncio
async def test_execution_uses_injected_job_persistence(monkeypatch):
    settings = Settings(environment="test", public_base_url="http://backend:8000")
    monkeypatch.setattr(monitor_engine, "get_settings", lambda: settings)
    monitor = Monitor(
        id=uuid.uuid4(),
        target_key="MOCK_HEALTHY",
        name="Mock Healthy API",
        url="http://backend:8000/demo/healthy",
        source_kind="MOCK",
        validation_profile="STATUS_SUCCESS",
        expected_status=200,
        max_latency_ms=2000,
        check_interval_minutes=5,
    )
    saved: list[tuple[str, uuid.UUID, str]] = []

    async def fake_probe(_monitor: Monitor, _client: httpx.AsyncClient):
        return monitor_engine.ProbeResult(
            checked_at=datetime.now(UTC),
            status="UP",
            http_status=200,
        )

    def claim_due(execution_id: str) -> list[Monitor]:
        assert execution_id == "injected-execution"
        return [monitor]

    def save_result(execution_id: str, monitor_id: uuid.UUID, result) -> bool:
        saved.append((execution_id, monitor_id, result.status))
        return True

    monkeypatch.setattr(monitor_engine, "probe_monitor", fake_probe)
    summary = await monitor_engine.execute_due_monitors(
        "injected-execution",
        claim_due=claim_due,
        save_result=save_result,
    )

    assert summary == {
        "execution_id": "injected-execution",
        "claimed": 1,
        "saved": 1,
        "down": 0,
    }
    assert saved == [("injected-execution", monitor.id, "UP")]
