from __future__ import annotations

from typing import Protocol
from typing import Sequence

from src.weather_comment_publishing.types import CityQuery, Coordinates, CurrentWeather, ForecastEntry, ResolvedLocation


class WeatherProviderPort(Protocol):
    async def resolve_city(self, query: CityQuery) -> ResolvedLocation: ...

    async def get_current_weather(self, coordinates: Coordinates) -> CurrentWeather: ...

    async def get_five_day_forecast(self, coordinates: Coordinates) -> list[ForecastEntry]: ...


class GistPublisherPort(Protocol):
    async def publish_comment(self, gist_id: str, content: str) -> int: ...


class WeatherCommentFormatterPort(Protocol):
    def format_comment(
        self,
        *,
        location: ResolvedLocation,
        current_weather: CurrentWeather,
        forecast_entries: Sequence[ForecastEntry],
    ) -> str: ...
