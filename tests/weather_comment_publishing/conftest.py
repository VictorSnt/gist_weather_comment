from __future__ import annotations

from datetime import UTC, datetime

import pytest
from faker import Faker

from src.weather_comment_publishing.types import (
    Coordinates,
    CurrentWeather,
    ForecastEntry,
    ResolvedLocation,
    WeatherCondition,
)


@pytest.fixture
def faker() -> Faker:
    instance = Faker("pt_BR")
    instance.seed_instance(42)
    return instance


@pytest.fixture
def weather_condition(faker: Faker) -> WeatherCondition:
    return WeatherCondition(
        code=803,
        group=faker.word().title(),
        description=faker.word().lower(),
        icon="04d",
    )


@pytest.fixture
def coordinates(faker: Faker) -> Coordinates:
    return Coordinates(
        latitude=float(faker.latitude()),
        longitude=float(faker.longitude()),
    )


@pytest.fixture
def resolved_location(faker: Faker, coordinates: Coordinates) -> ResolvedLocation:
    return ResolvedLocation(
        name=faker.city(),
        state=faker.lexify(text="?????").title(),
        country="BR",
        coordinates=coordinates,
    )


@pytest.fixture
def current_weather(faker: Faker, weather_condition: WeatherCondition) -> CurrentWeather:
    return CurrentWeather(
        temperature_celsius=float(faker.pydecimal(min_value=10, max_value=40, right_digits=1)),
        condition=weather_condition,
        observed_at=datetime(2026, 3, 11, 12, 0, tzinfo=UTC),
    )


@pytest.fixture
def forecast_entries(current_weather: CurrentWeather) -> list[ForecastEntry]:
    return [
        ForecastEntry(
            forecasted_at=current_weather.observed_at.replace(day=12, hour=hour, minute=0),
            temperature_celsius=temp,
        )
        for hour, temp in [(0, 26.0), (12, 30.0), (18, 28.0)]
    ]
