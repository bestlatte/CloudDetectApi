import json
from datetime import date

import pytest

from app.services.validators import validate_http_payload


def validate(profile: str, payload, **overrides):
    values = {
        "profile": profile,
        "expected_status": 200,
        "http_status": 200,
        "content_type": "application/json; charset=utf-8",
        "body": json.dumps(payload).encode(),
        "latency_ms": 100,
        "max_latency_ms": 2000,
        "stale_after_days": 5,
        "today": date(2026, 10, 19),
    }
    values.update(overrides)
    return validate_http_payload(**values)


def test_healthy_mock_is_up():
    assert validate("STATUS_SUCCESS", {"status": "success"}).status == "UP"


def test_http_500_precedes_json_validation():
    result = validate("STATUS_SUCCESS", {"status": "success"}, http_status=500)
    assert (result.status, result.reason_code) == ("DOWN", "HTTP_STATUS_MISMATCH")


def test_slow_valid_response_is_degraded():
    result = validate("STATUS_SUCCESS", {"status": "success"}, latency_ms=3000)
    assert (result.status, result.reason_code) == ("DEGRADED", "SLOW_RESPONSE")


def test_business_error_is_down():
    result = validate("STATUS_SUCCESS", {"status": "error"})
    assert result.reason_code == "BUSINESS_RULE_MISMATCH"


def test_frankfurter_fixture_is_valid():
    result = validate(
        "FRANKFURTER_V2",
        {"date": "2026-10-19", "base": "USD", "quote": "TWD", "rate": 31.5},
    )
    assert result.status == "UP"
    assert result.source_data_date == date(2026, 10, 19)


@pytest.mark.parametrize("missing", ["date", "base", "quote", "rate"])
def test_frankfurter_requires_all_fields(missing):
    payload = {"date": "2026-10-19", "base": "USD", "quote": "TWD", "rate": 31.5}
    payload.pop(missing)
    assert validate("FRANKFURTER_V2", payload).reason_code == "SCHEMA_MISMATCH"


@pytest.mark.parametrize("rate", [0, -1, float("nan"), float("inf")])
def test_frankfurter_rejects_invalid_rates(rate):
    payload = {"date": "2026-10-19", "base": "USD", "quote": "TWD", "rate": rate}
    assert validate("FRANKFURTER_V2", payload).reason_code == "BUSINESS_RULE_MISMATCH"


@pytest.mark.parametrize(
    ("field", "value"),
    [("date", 20261019), ("base", ["USD"]), ("quote", None), ("rate", "31.5"), ("rate", True)],
)
def test_frankfurter_rejects_wrong_field_types(field, value):
    payload = {"date": "2026-10-19", "base": "USD", "quote": "TWD", "rate": 31.5}
    payload[field] = value
    assert validate("FRANKFURTER_V2", payload).reason_code == "SCHEMA_MISMATCH"


def test_old_source_date_is_warning_not_outage():
    payload = {"date": "2026-10-10", "base": "USD", "quote": "TWD", "rate": 31.5}
    result = validate("FRANKFURTER_V2", payload)
    assert result.status == "UP"
    assert result.data_warning == "STALE_DATA"


def test_weekend_age_is_note_not_outage():
    payload = {"date": "2026-10-16", "base": "USD", "quote": "TWD", "rate": 31.5}
    result = validate("FRANKFURTER_V2", payload)
    assert result.status == "UP"
    assert result.data_warning == "DATA_DATE_NOTE"


def test_rate_limit_has_explicit_reason():
    result = validate("FRANKFURTER_V2", {}, http_status=429)
    assert (result.status, result.reason_code) == ("DOWN", "RATE_LIMITED")


def test_non_json_content_type_is_rejected():
    result = validate("STATUS_SUCCESS", {"status": "success"}, content_type="text/html")
    assert result.reason_code == "CONTENT_TYPE_MISMATCH"


def test_invalid_json_is_rejected_after_content_type():
    result = validate("STATUS_SUCCESS", {}, body=b"not-json")
    assert result.reason_code == "INVALID_JSON"


def test_non_object_json_is_a_schema_mismatch():
    result = validate("STATUS_SUCCESS", [], body=b"[]")
    assert result.reason_code == "SCHEMA_MISMATCH"


def test_mock_status_type_is_a_schema_mismatch():
    result = validate("STATUS_SUCCESS", {"status": True})
    assert result.reason_code == "SCHEMA_MISMATCH"


def test_github_rate_limit_fixture_is_valid():
    payload = {"rate": {"limit": 60, "remaining": 57, "reset": 1792380000}}
    assert validate("GITHUB_RATE_LIMIT", payload).status == "UP"


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"rate": []},
        {"rate": {"limit": 60, "remaining": 57}},
        {"rate": {"limit": "60", "remaining": 57, "reset": 1792380000}},
    ],
)
def test_github_rate_limit_schema_mismatches(payload):
    assert validate("GITHUB_RATE_LIMIT", payload).reason_code == "SCHEMA_MISMATCH"


def test_open_meteo_current_fixture_is_valid():
    payload = {
        "latitude": 25.0,
        "longitude": 121.5,
        "current": {"time": "2026-10-20T00:00", "temperature_2m": 24.6},
    }
    assert validate("OPEN_METEO_CURRENT", payload).status == "UP"


@pytest.mark.parametrize(
    "payload",
    [
        {"latitude": 25.0, "longitude": 121.5},
        {"latitude": "25", "longitude": 121.5, "current": {}},
        {"latitude": 25.0, "longitude": 121.5, "current": {"time": 123, "temperature_2m": 24}},
        {"latitude": 25.0, "longitude": 121.5, "current": {"time": "now", "temperature_2m": "24"}},
    ],
)
def test_open_meteo_schema_mismatches(payload):
    assert validate("OPEN_METEO_CURRENT", payload).reason_code == "SCHEMA_MISMATCH"


def test_pokeapi_species_fixture_is_valid():
    assert validate("POKEAPI_SPECIES", {"id": 25, "name": "pikachu"}).status == "UP"


def test_pokeapi_rejects_wrong_resource():
    result = validate("POKEAPI_SPECIES", {"id": 1, "name": "bulbasaur"})
    assert result.reason_code == "BUSINESS_RULE_MISMATCH"


def test_unknown_validation_profile_is_rejected():
    result = validate("UNKNOWN_PROFILE", {"status": "success"})
    assert result.reason_code == "VALIDATION_PROFILE_UNSUPPORTED"

