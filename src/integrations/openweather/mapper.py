from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, timezone

from src.weather_comment_publishing.types import (
    Coordinates,
    CurrentWeather,
    ForecastEntry,
    ResolvedLocation,
    WeatherCondition,
)
from src.integrations.openweather.schemas import (
    CurrentWeatherPayload,
    ForecastPayload,
    GeocodingLocationPayload,
    WeatherConditionPayload,
)


@dataclass(frozen=True, slots=True)
class OpenWeatherMapper:
    def to_resolved_location(self, payload: GeocodingLocationPayload) -> ResolvedLocation:
        return ResolvedLocation(
            name=payload.name,
            state=payload.state,
            country=payload.country,
            coordinates=Coordinates(latitude=payload.lat, longitude=payload.lon),
        )

    def to_current_weather(self, payload: CurrentWeatherPayload) -> CurrentWeather:
        primary_condition_payload = payload.weather[0]
        return CurrentWeather(
            temperature_celsius=payload.main.temp,
            condition=self._to_condition(primary_condition_payload),
            observed_at=self._to_local_datetime(payload.dt, self._get_timezone_offset(payload)),
        )

    def to_forecast_entries(self, payload: ForecastPayload) -> list[ForecastEntry]:
        timezone_offset = self._get_timezone_offset(payload)
        return [
            ForecastEntry(
                temperature_celsius=item.main.temp,
                forecasted_at=self._to_local_datetime(item.dt, timezone_offset),
            )
            for item in payload.list
        ]

    def _get_timezone_offset(self, payload: CurrentWeatherPayload | ForecastPayload) -> int:
        if payload.timezone is not None:
            return payload.timezone
        if isinstance(payload, ForecastPayload) and payload.city and payload.city.timezone is not None:
            return payload.city.timezone
        return 0

    def _to_local_datetime(self, timestamp: int, timezone_offset: int) -> datetime:
        local_timezone = timezone(timedelta(seconds=timezone_offset))
        return datetime.fromtimestamp(timestamp, tz=UTC).astimezone(local_timezone)

    def _to_condition(self, payload: WeatherConditionPayload) -> WeatherCondition:
        return WeatherCondition(
            code=payload.id,
            group=payload.main,
            description=payload.description,
            icon=payload.icon,
        )
