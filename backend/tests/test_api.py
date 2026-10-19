from app.db.seed import seed_monitors

ORIGIN = {"Origin": "http://testserver"}


def login(client):
    response = client.post(
        "/api/v1/auth/login",
        headers=ORIGIN,
        json={"password": "test-admin-password"},
    )
    assert response.status_code == 200
    csrf = client.cookies.get("cloudpulse_csrf")
    return {**ORIGIN, "X-CSRF-Token": csrf}


def test_public_health_and_overview(client):
    seed_monitors()
    assert client.get("/health").json()["status"] == "ok"
    overview = client.get("/api/v1/overview")
    assert overview.status_code == 200
    assert overview.json()["total_targets"] == 8
    assert overview.json()["real"]["unknown"] == 4


def test_four_demo_endpoints_expose_expected_scenarios(client):
    assert client.get("/demo/healthy").status_code == 200
    assert client.get("/demo/healthy").json()["status"] == "success"
    assert client.get("/demo/server-error").status_code == 500
    assert client.get("/demo/business-error").json()["status"] == "error"


def test_anonymous_write_is_rejected(client):
    response = client.post("/api/v1/monitors", headers=ORIGIN, json={"target_key": "MOCK_HEALTHY"})
    assert response.status_code == 401


def test_login_requires_approved_origin(client):
    response = client.post("/api/v1/auth/login", json={"password": "test-admin-password"})
    assert response.status_code == 403


def test_admin_cannot_create_arbitrary_target(client):
    headers = login(client)
    response = client.post(
        "/api/v1/monitors",
        headers=headers,
        json={"target_key": "https://metadata.google.internal"},
    )
    assert response.status_code == 422


def test_real_target_rejects_short_interval(client):
    headers = login(client)
    response = client.post(
        "/api/v1/monitors",
        headers=headers,
        json={"target_key": "FRANKFURTER_USD_TWD", "check_interval_minutes": 5},
    )
    assert response.status_code == 422


def test_soft_delete_preserves_history_contract(client):
    seed_monitors()
    headers = login(client)
    monitors = client.get("/api/v1/monitors?include_disabled=true").json()
    target = next(item for item in monitors if item["target_key"] == "MOCK_HEALTHY")
    assert client.delete(f"/api/v1/monitors/{target['id']}", headers=headers).status_code == 204
    assert all(item["id"] != target["id"] for item in client.get("/api/v1/monitors").json())
    restored = client.post("/api/v1/monitors", headers=headers, json={"target_key": "MOCK_HEALTHY"})
    assert restored.status_code == 201
    assert restored.json()["id"] == target["id"]

