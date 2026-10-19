from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings


@dataclass(frozen=True)
class TargetTemplate:
    key: str
    default_name: str
    path_or_url: str
    source_kind: str
    validation_profile: str
    expected_status: int
    max_latency_ms: int
    check_interval_minutes: int

    def resolved_url(self, settings: Settings) -> str:
        if self.path_or_url.startswith("https://"):
            return self.path_or_url
        return f"{settings.public_base_url.rstrip('/')}{self.path_or_url}"


TARGET_TEMPLATES: dict[str, TargetTemplate] = {
    "FRANKFURTER_USD_TWD": TargetTemplate(
        key="FRANKFURTER_USD_TWD",
        default_name="Frankfurter USD/TWD",
        path_or_url="https://api.frankfurter.dev/v2/rate/usd/twd",
        source_kind="REAL",
        validation_profile="FRANKFURTER_V2",
        expected_status=200,
        max_latency_ms=2000,
        check_interval_minutes=60,
    ),
    "GITHUB_RATE_LIMIT": TargetTemplate(
        key="GITHUB_RATE_LIMIT",
        default_name="GitHub REST API",
        path_or_url="https://api.github.com/rate_limit",
        source_kind="REAL",
        validation_profile="GITHUB_RATE_LIMIT",
        expected_status=200,
        max_latency_ms=2000,
        check_interval_minutes=60,
    ),
    "OPEN_METEO_TAIPEI": TargetTemplate(
        key="OPEN_METEO_TAIPEI",
        default_name="Open-Meteo Taipei",
        path_or_url=(
            "https://api.open-meteo.com/v1/forecast?latitude=25.0375&longitude=121.5637"
            "&current=temperature_2m&timezone=Asia%2FTaipei"
        ),
        source_kind="REAL",
        validation_profile="OPEN_METEO_CURRENT",
        expected_status=200,
        max_latency_ms=2500,
        check_interval_minutes=60,
    ),
    "POKEAPI_PIKACHU": TargetTemplate(
        key="POKEAPI_PIKACHU",
        default_name="PokéAPI Pikachu",
        path_or_url="https://pokeapi.co/api/v2/pokemon-species/pikachu",
        source_kind="REAL",
        validation_profile="POKEAPI_SPECIES",
        expected_status=200,
        max_latency_ms=2500,
        check_interval_minutes=60,
    ),
    "MOCK_HEALTHY": TargetTemplate(
        key="MOCK_HEALTHY",
        default_name="Mock Healthy API",
        path_or_url="/demo/healthy",
        source_kind="MOCK",
        validation_profile="STATUS_SUCCESS",
        expected_status=200,
        max_latency_ms=2000,
        check_interval_minutes=5,
    ),
    "MOCK_SERVER_ERROR": TargetTemplate(
        key="MOCK_SERVER_ERROR",
        default_name="Mock Server Error",
        path_or_url="/demo/server-error",
        source_kind="MOCK",
        validation_profile="HTTP_ONLY",
        expected_status=200,
        max_latency_ms=2000,
        check_interval_minutes=5,
    ),
    "MOCK_SLOW": TargetTemplate(
        key="MOCK_SLOW",
        default_name="Mock Slow API",
        path_or_url="/demo/slow",
        source_kind="MOCK",
        validation_profile="STATUS_SUCCESS",
        expected_status=200,
        max_latency_ms=2000,
        check_interval_minutes=5,
    ),
    "MOCK_BUSINESS_ERROR": TargetTemplate(
        key="MOCK_BUSINESS_ERROR",
        default_name="Mock Business Error",
        path_or_url="/demo/business-error",
        source_kind="MOCK",
        validation_profile="STATUS_SUCCESS",
        expected_status=200,
        max_latency_ms=2000,
        check_interval_minutes=5,
    ),
}


def get_target_template(target_key: str) -> TargetTemplate:
    try:
        return TARGET_TEMPLATES[target_key]
    except KeyError as exc:
        raise ValueError("Target is not in the approved template list.") from exc

