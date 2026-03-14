from __future__ import annotations

from datetime import UTC, datetime

import pytest

from src.weather_comment_publishing.types import (
    Coordinates,
    CurrentWeather,
    ForecastEntry,
    ResolvedLocation,
    WeatherCondition,
)


@pytest.fixture
def weather_condition() -> WeatherCondition:
    return WeatherCondition(code=803, group="Clouds", description="nublado", icon="04d")


@pytest.fixture
def coordinates() -> Coordinates:
    return Coordinates(latitude=-23.55, longitude=-46.63)


@pytest.fixture
def resolved_location(coordinates: Coordinates) -> ResolvedLocation:
    return ResolvedLocation(
        name="Sao Paulo",
        state="SP",
        country="BR",
        coordinates=coordinates,
    )


@pytest.fixture
def current_weather(weather_condition: WeatherCondition) -> CurrentWeather:
    return CurrentWeather(
        temperature_celsius=31.4,
        condition=weather_condition,
        observed_at=datetime(2026, 3, 11, 12, 0, tzinfo=UTC),
    )


@pytest.fixture
def forecast_entries() -> list[ForecastEntry]:
    return [
        ForecastEntry(
            forecasted_at=datetime(2026, 3, 12, hour, 0, tzinfo=UTC),
            temperature_celsius=temp,
        )
        for hour, temp in [(0, 26.0), (12, 30.0), (18, 28.0)]
    ]
