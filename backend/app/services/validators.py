from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import date
from typing import Any


@dataclass(frozen=True)
class ValidationOutcome:
    status: str
    reason_code: str | None = None
    error_summary: str | None = None
    source_data_date: date | None = None
    data_warning: str | None = None


def _down(reason: str, summary: str) -> ValidationOutcome:
    return ValidationOutcome(status="DOWN", reason_code=reason, error_summary=summary[:500])


def validate_http_payload(
    *,
    profile: str,
    expected_status: int,
    http_status: int,
    content_type: str,
    body: bytes,
    latency_ms: int,
    max_latency_ms: int,
    stale_after_days: int,
    today: date | None = None,
) -> ValidationOutcome:
    if http_status == 429:
        return _down("RATE_LIMITED", "The target rejected the request due to rate limiting.")
    if http_status != expected_status:
        return _down(
            "HTTP_STATUS_MISMATCH",
            f"Expected HTTP {expected_status}, received HTTP {http_status}.",
        )

    payload: Any = None
    if profile != "HTTP_ONLY":
        normalized_content_type = content_type.split(";", 1)[0].strip().lower()
        known_json_type = normalized_content_type in {"application/json", "application/problem+json"}
        if not known_json_type and not normalized_content_type.endswith("+json"):
            return _down("CONTENT_TYPE_MISMATCH", "Expected a JSON response content type.")
        try:
            payload = json.loads(body)
        except (UnicodeDecodeError, json.JSONDecodeError):
            return _down("INVALID_JSON", "The response body is not valid JSON.")
        if not isinstance(payload, dict):
            return _down("SCHEMA_MISMATCH", "The JSON response must be an object.")

    source_data_date: date | None = None
    data_warning: str | None = None
    if profile == "STATUS_SUCCESS":
        if "status" not in payload:
            return _down("SCHEMA_MISMATCH", "The JSON response is missing the status field.")
        if not isinstance(payload["status"], str):
            return _down("SCHEMA_MISMATCH", "The status field must be a string.")
        if payload["status"] != "success":
            return _down("BUSINESS_RULE_MISMATCH", "Expected status=success in the JSON response.")
    elif profile == "FRANKFURTER_V2":
        required = {"date", "base", "quote", "rate"}
        missing = sorted(required.difference(payload))
        if missing:
            return _down("SCHEMA_MISMATCH", f"Missing required JSON fields: {', '.join(missing)}.")
        if not all(isinstance(payload[field], str) for field in ("date", "base", "quote")):
            return _down("SCHEMA_MISMATCH", "The date, base and quote fields must be strings.")
        rate = payload["rate"]
        if isinstance(rate, bool) or not isinstance(rate, (int, float)):
            return _down("SCHEMA_MISMATCH", "The rate field must be a number.")
        if payload["base"] != "USD" or payload["quote"] != "TWD":
            return _down("BUSINESS_RULE_MISMATCH", "Expected the USD/TWD currency pair.")
        if not math.isfinite(rate) or rate <= 0:
            return _down("BUSINESS_RULE_MISMATCH", "The rate must be a finite number greater than zero.")
        try:
            source_data_date = date.fromisoformat(payload["date"])
        except (TypeError, ValueError):
            return _down("BUSINESS_RULE_MISMATCH", "The date must use YYYY-MM-DD format.")
        age_days = ((today or date.today()) - source_data_date).days
        if age_days > stale_after_days:
            data_warning = "STALE_DATA"
        elif age_days > 0:
            data_warning = "DATA_DATE_NOTE"
    elif profile == "GITHUB_RATE_LIMIT":
        rate = payload.get("rate")
        if not isinstance(rate, dict):
            return _down("SCHEMA_MISMATCH", "The JSON response must contain a rate object.")
        required = {"limit", "remaining", "reset"}
        missing = sorted(required.difference(rate))
        if missing:
            return _down("SCHEMA_MISMATCH", f"Missing rate fields: {', '.join(missing)}.")
        if any(isinstance(rate[field], bool) or not isinstance(rate[field], int) for field in required):
            return _down("SCHEMA_MISMATCH", "GitHub rate fields must be integers.")
        if rate["limit"] <= 0 or rate["remaining"] < 0 or rate["reset"] <= 0:
            return _down("BUSINESS_RULE_MISMATCH", "GitHub rate-limit values are outside valid ranges.")
    elif profile == "OPEN_METEO_CURRENT":
        required = {"latitude", "longitude", "current"}
        missing = sorted(required.difference(payload))
        if missing:
            return _down("SCHEMA_MISMATCH", f"Missing weather fields: {', '.join(missing)}.")
        if not all(
            isinstance(payload[field], (int, float)) and not isinstance(payload[field], bool)
            for field in ("latitude", "longitude")
        ):
            return _down("SCHEMA_MISMATCH", "Weather coordinates must be numbers.")
        current = payload["current"]
        if not isinstance(current, dict) or not {"time", "temperature_2m"}.issubset(current):
            return _down("SCHEMA_MISMATCH", "Current weather fields are incomplete.")
        temperature = current["temperature_2m"]
        if not isinstance(current["time"], str):
            return _down("SCHEMA_MISMATCH", "The current weather time must be a string.")
        if isinstance(temperature, bool) or not isinstance(temperature, (int, float)):
            return _down("SCHEMA_MISMATCH", "The current temperature must be a number.")
        if not math.isfinite(temperature):
            return _down("BUSINESS_RULE_MISMATCH", "The current temperature must be finite.")
    elif profile == "POKEAPI_SPECIES":
        required = {"id", "name"}
        missing = sorted(required.difference(payload))
        if missing:
            return _down("SCHEMA_MISMATCH", f"Missing Pokémon fields: {', '.join(missing)}.")
        if isinstance(payload["id"], bool) or not isinstance(payload["id"], int):
            return _down("SCHEMA_MISMATCH", "The Pokémon id must be an integer.")
        if not isinstance(payload["name"], str):
            return _down("SCHEMA_MISMATCH", "The Pokémon name must be a string.")
        if payload["id"] != 25 or payload["name"].lower() != "pikachu":
            return _down("BUSINESS_RULE_MISMATCH", "Expected the Pikachu species resource.")
    elif profile != "HTTP_ONLY":
        return _down("VALIDATION_PROFILE_UNSUPPORTED", "The validation profile is not supported.")

    if latency_ms > max_latency_ms:
        return ValidationOutcome(
            status="DEGRADED",
            reason_code="SLOW_RESPONSE",
            error_summary=f"Latency {latency_ms}ms exceeded the {max_latency_ms}ms threshold.",
            source_data_date=source_data_date,
            data_warning=data_warning,
        )
    return ValidationOutcome(
        status="UP",
        source_data_date=source_data_date,
        data_warning=data_warning,
    )

