from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import pytest

from src.shared.exceptions import (
    GitHubGistIntegrationError,
    LocationNotFoundError,
    WeatherProviderError,
)
from src.weather_comment_publishing.service import WeatherCommentService
from src.weather_comment_publishing.types import (
    CityQuery,
    Coordinates,
    CurrentWeather,
    ForecastEntry,
    ResolvedLocation,
)


@dataclass
class FakeWeatherProvider:
    resolved_location: ResolvedLocation
    current_weather: CurrentWeather
    forecast_entries: list[ForecastEntry]
    events: list[str]
    resolve_error: Exception | None = None
    current_error: Exception | None = None
    forecast_error: Exception | None = None
    received_query: CityQuery | None = None
    received_current_coordinates: Coordinates | None = None
    received_forecast_coordinates: Coordinates | None = None

    async def resolve_city(self, query: CityQuery) -> ResolvedLocation:
        self.events.append("resolve_city")
        self.received_query = query
        if self.resolve_error:
            raise self.resolve_error
        return self.resolved_location

    async def get_current_weather(self, coordinates: Coordinates) -> CurrentWeather:
        self.events.append("get_current_weather")
        self.received_current_coordinates = coordinates
        if self.current_error:
            raise self.current_error
        return self.current_weather

    async def get_five_day_forecast(self, coordinates: Coordinates) -> list[ForecastEntry]:
        self.events.append("get_five_day_forecast")
        self.received_forecast_coordinates = coordinates
        if self.forecast_error:
            raise self.forecast_error
        return self.forecast_entries


@dataclass
class FakeFormatter:
    comment: str
    events: list[str]
    received_location: ResolvedLocation | None = None
    received_weather: CurrentWeather | None = None
    received_forecast: list[ForecastEntry] | None = None

    def format_comment(
        self,
        *,
        location: ResolvedLocation,
        current_weather: CurrentWeather,
        forecast_entries: Sequence[ForecastEntry],
    ) -> str:
        self.events.append("format_comment")
        self.received_location = location
        self.received_weather = current_weather
        self.received_forecast = list(forecast_entries)
        return self.comment


@dataclass
class FakeGistPublisher:
    comment_id: int
    events: list[str]
    publish_error: Exception | None = None
    received_gist_id: str | None = None
    received_content: str | None = None

    async def publish_comment(self, gist_id: str, content: str) -> int:
        self.events.append("publish_comment")
        self.received_gist_id = gist_id
        self.received_content = content
        if self.publish_error:
            raise self.publish_error
        return self.comment_id


def make_query() -> CityQuery:
    return CityQuery(city="Sao Paulo", state="Sao Paulo", country="BR", zipcode=None)


def make_service(
    *,
    resolved_location: ResolvedLocation,
    current_weather: CurrentWeather,
    forecast_entries: list[ForecastEntry],
    resolve_error: Exception | None = None,
    current_error: Exception | None = None,
    forecast_error: Exception | None = None,
    publish_error: Exception | None = None,
) -> tuple[WeatherCommentService, FakeWeatherProvider, FakeFormatter, FakeGistPublisher, list[str]]:
    events: list[str] = []

    provider = FakeWeatherProvider(
        resolved_location=resolved_location,
        current_weather=current_weather,
        forecast_entries=forecast_entries,
        events=events,
        resolve_error=resolve_error,
        current_error=current_error,
        forecast_error=forecast_error,
    )
    formatter = FakeFormatter(comment="comentario final", events=events)
    publisher = FakeGistPublisher(
        comment_id=123,
        events=events,
        publish_error=publish_error,
    )
    service = WeatherCommentService(
        openweather_client=provider,
        github_gist_client=publisher,
        formatter=formatter,
    )
    return service, provider, formatter, publisher, events


class TestWeatherCommentService:
    @pytest.mark.asyncio
    async def test_publish_weather_comment_returns_result_and_calls_dependencies_in_order(
        self,
        resolved_location: ResolvedLocation,
        current_weather: CurrentWeather,
        forecast_entries: list[ForecastEntry],
    ) -> None:
        service, provider, formatter, publisher, events = make_service(
            resolved_location=resolved_location,
            current_weather=current_weather,
            forecast_entries=forecast_entries,
        )

        result = await service.publish_weather_comment(
            gist_id="abc123",
            city_query=make_query(),
        )

        assert events == [
            "resolve_city",
            "get_current_weather",
            "get_five_day_forecast",
            "format_comment",
            "publish_comment",
        ]
        assert provider.received_current_coordinates == resolved_location.coordinates
        assert provider.received_forecast_coordinates == resolved_location.coordinates
        assert formatter.received_location == resolved_location
        assert formatter.received_weather == current_weather
        assert formatter.received_forecast == forecast_entries
        assert publisher.received_gist_id == "abc123"
        assert publisher.received_content == "comentario final"
        assert result.gist_id == "abc123"
        assert result.comment_id == 123
        assert result.location == resolved_location
        assert result.comment == "comentario final"

    @pytest.mark.asyncio
    async def test_publish_weather_comment_stops_when_city_cannot_be_resolved(
        self,
        resolved_location: ResolvedLocation,
        current_weather: CurrentWeather,
        forecast_entries: list[ForecastEntry],
    ) -> None:
        service, _, _, _, events = make_service(
            resolved_location=resolved_location,
            current_weather=current_weather,
            forecast_entries=forecast_entries,
            resolve_error=LocationNotFoundError("Location not found."),
        )

        with pytest.raises(LocationNotFoundError, match="Location not found."):
            await service.publish_weather_comment(
                gist_id="abc123",
                city_query=make_query(),
            )

        assert events == ["resolve_city"]

    @pytest.mark.asyncio
    async def test_publish_weather_comment_stops_when_current_weather_fails(
        self,
        resolved_location: ResolvedLocation,
        current_weather: CurrentWeather,
        forecast_entries: list[ForecastEntry],
    ) -> None:
        service, _, _, _, events = make_service(
            resolved_location=resolved_location,
            current_weather=current_weather,
            forecast_entries=forecast_entries,
            current_error=WeatherProviderError("upstream failed"),
        )

        with pytest.raises(WeatherProviderError, match="upstream failed"):
            await service.publish_weather_comment(
                gist_id="abc123",
                city_query=make_query(),
            )

        assert events == ["resolve_city", "get_current_weather"]

    @pytest.mark.asyncio
    async def test_publish_weather_comment_stops_when_forecast_fails(
        self,
        resolved_location: ResolvedLocation,
        current_weather: CurrentWeather,
        forecast_entries: list[ForecastEntry],
    ) -> None:
        service, _, _, _, events = make_service(
            resolved_location=resolved_location,
            current_weather=current_weather,
            forecast_entries=forecast_entries,
            forecast_error=WeatherProviderError("forecast unavailable"),
        )

        with pytest.raises(WeatherProviderError, match="forecast unavailable"):
            await service.publish_weather_comment(
                gist_id="abc123",
                city_query=make_query(),
            )

        assert events == [
            "resolve_city",
            "get_current_weather",
            "get_five_day_forecast",
        ]

    @pytest.mark.asyncio
    async def test_publish_weather_comment_propagates_gist_publish_error_after_formatting(
        self,
        resolved_location: ResolvedLocation,
        current_weather: CurrentWeather,
        forecast_entries: list[ForecastEntry],
    ) -> None:
        service, _, formatter, publisher, events = make_service(
            resolved_location=resolved_location,
            current_weather=current_weather,
            forecast_entries=forecast_entries,
            publish_error=GitHubGistIntegrationError("github unavailable"),
        )

        with pytest.raises(GitHubGistIntegrationError, match="github unavailable"):
            await service.publish_weather_comment(
                gist_id="abc123",
                city_query=make_query(),
            )

        assert events == [
            "resolve_city",
            "get_current_weather",
            "get_five_day_forecast",
            "format_comment",
            "publish_comment",
        ]
        assert formatter.received_location == resolved_location
        assert publisher.received_content == "comentario final"