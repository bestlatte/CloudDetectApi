from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from app.db.seed import seed_monitors

ORIGIN = {"Origin": "http://testserver"}


def _login(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        headers=ORIGIN,
        json={"password": "test-admin-password"},
    )
    assert response.status_code == 200
    assert response.json()["authenticated"] is True
    csrf_token = client.cookies.get("cloudpulse_csrf")
    assert csrf_token is not None
    return {**ORIGIN, "X-CSRF-Token": csrf_token}


def test_login_session_and_logout_csrf_contract(client: TestClient) -> None:
    write_headers = _login(client)

    active_session = client.get("/api/v1/auth/session")
    assert active_session.status_code == 200
    assert active_session.json()["authenticated"] is True
    assert active_session.json()["expires_at"] is not None

    missing_csrf = client.post("/api/v1/auth/logout", headers=ORIGIN)
    assert missing_csrf.status_code == 403
    assert client.get("/api/v1/auth/session").json()["authenticated"] is True

    logout = client.post("/api/v1/auth/logout", headers=write_headers)
    assert logout.status_code == 204

    ended_session = client.get("/api/v1/auth/session")
    assert ended_session.status_code == 200
    assert ended_session.json() == {"authenticated": False, "expires_at": None}


def test_seeded_target_cannot_be_created_twice(client: TestClient) -> None:
    assert seed_monitors() == 8
    write_headers = _login(client)

    duplicate = client.post(
        "/api/v1/monitors",
        headers=write_headers,
        json={"target_key": "MOCK_HEALTHY"},
    )

    assert duplicate.status_code == 409
    assert duplicate.json()["detail"] == "This approved target already exists."


def test_missing_monitor_routes_return_not_found(client: TestClient) -> None:
    write_headers = _login(client)
    missing_monitor_id = uuid.uuid4()

    update = client.patch(
        f"/api/v1/monitors/{missing_monitor_id}",
        headers=write_headers,
        json={"name": "Missing monitor"},
    )
    delete = client.delete(
        f"/api/v1/monitors/{missing_monitor_id}",
        headers=write_headers,
    )
    nested_checks = client.get(f"/api/v1/monitors/{missing_monitor_id}/checks")

    assert update.status_code == 404
    assert delete.status_code == 404
    assert nested_checks.status_code == 404


def test_overview_and_monitor_filters_keep_real_and_mock_unknowns_separate(client: TestClient) -> None:
    assert seed_monitors() == 8

    overview_response = client.get("/api/v1/overview")
    assert overview_response.status_code == 200
    overview = overview_response.json()
    assert overview["total_targets"] == 8
    assert overview["real"] == {"up": 0, "down": 0, "degraded": 0, "unknown": 4}
    assert overview["mock"] == {"up": 0, "down": 0, "degraded": 0, "unknown": 4}

    real_response = client.get("/api/v1/monitors?source_kind=REAL&health_status=UNKNOWN")
    mock_response = client.get("/api/v1/monitors?source_kind=MOCK&health_status=UNKNOWN")
    assert real_response.status_code == 200
    assert mock_response.status_code == 200

    real_monitors = real_response.json()
    mock_monitors = mock_response.json()
    assert len(real_monitors) == overview["real"]["unknown"] == 4
    assert len(mock_monitors) == overview["mock"]["unknown"] == 4
    assert {monitor["source_kind"] for monitor in real_monitors} == {"REAL"}
    assert {monitor["source_kind"] for monitor in mock_monitors} == {"MOCK"}
    assert {monitor["latest_status"] for monitor in real_monitors + mock_monitors} == {"UNKNOWN"}
    assert {monitor["id"] for monitor in real_monitors}.isdisjoint(
        monitor["id"] for monitor in mock_monitors
    )
