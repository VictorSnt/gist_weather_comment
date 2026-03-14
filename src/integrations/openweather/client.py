from __future__ import annotations

from dataclasses import dataclass, field
import unicodedata
from typing import Any, TypeVar, overload

import httpx
from pydantic import BaseModel, TypeAdapter, ValidationError as PydanticValidationError

from src.weather_comment_publishing.types import CityQuery, Coordinates, CurrentWeather, ForecastEntry, ResolvedLocation
from src.integrations.openweather.mapper import OpenWeatherMapper
from src.integrations.openweather.schemas import (
    CurrentWeatherPayload,
    ForecastPayload,
    GEOCODING_LOCATIONS,
    GeocodingLocationPayload,
)
from src.shared.exceptions import (
    LocationAmbiguousError,
    LocationNotFoundError,
    WeatherProviderError,
)

ModelT = TypeVar("ModelT", bound=BaseModel)
ParsedT = TypeVar("ParsedT")


@dataclass(frozen=True, slots=True)
class OpenWeatherApiClient:
    api_key: str
    base_url: str
    language: str
    units: str
    timeout_seconds: float
    mapper: OpenWeatherMapper = field(default_factory=OpenWeatherMapper)

    async def resolve_city(self, query: CityQuery) -> ResolvedLocation:
        payload = await self._request_json(
            endpoint="/geo/1.0/direct",
            params={
                "q": self._build_geocoding_query(query),
                "limit": "5",
                "appid": self.api_key,
            },
            error_message="Failed to resolve location from OpenWeather.",
        )
        locations = self._parse_payload(
            GEOCODING_LOCATIONS,
            payload,
            error_message="Invalid OpenWeather geocoding payload.",
        )
        matches = [location for location in locations if self._matches_geolocation_filters(location, query)]

        if not matches:
            raise LocationNotFoundError("Location not found.")
        if len(matches) > 1:
            raise LocationAmbiguousError("Location is ambiguous.")

        return self.mapper.to_resolved_location(matches[0])

    async def get_current_weather(self, coordinates: Coordinates) -> CurrentWeather:
        payload = await self._request_json(
            endpoint="/data/2.5/weather",
            params={
                "lat": str(coordinates.latitude),
                "lon": str(coordinates.longitude),
                "units": self.units,
                "lang": self.language,
                "appid": self.api_key,
            },
            error_message="Failed to read current weather from OpenWeather.",
        )
        current = self._parse_payload(
            CurrentWeatherPayload,
            payload,
            error_message="Invalid OpenWeather current weather payload.",
        )
        return self.mapper.to_current_weather(current)

    async def get_five_day_forecast(self, coordinates: Coordinates) -> list[ForecastEntry]:
        payload = await self._request_json(
            endpoint="/data/2.5/forecast",
            params={
                "lat": str(coordinates.latitude),
                "lon": str(coordinates.longitude),
                "units": self.units,
                "lang": self.language,
                "appid": self.api_key,
            },
            error_message="Failed to read forecast from OpenWeather.",
        )
        forecast = self._parse_payload(
            ForecastPayload,
            payload,
            error_message="Invalid OpenWeather forecast payload.",
        )
        return self.mapper.to_forecast_entries(forecast)

    async def _request_json(
        self,
        *,
        endpoint: str,
        params: dict[str, str],
        error_message: str,
    ) -> object:
        url = f"{self.base_url.rstrip('/')}{endpoint}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as exc:
            raise WeatherProviderError(error_message) from exc

    @overload
    def _parse_payload(
        self,
        schema: type[ModelT],
        payload: object,
        *,
        error_message: str,
    ) -> ModelT: ...

    @overload
    def _parse_payload(
        self,
        schema: TypeAdapter[ParsedT],
        payload: object,
        *,
        error_message: str,
    ) -> ParsedT: ...

    def _parse_payload(
        self,
        schema: type[BaseModel] | TypeAdapter[Any],
        payload: object,
        *,
        error_message: str,
    ) -> Any:
        try:
            if isinstance(schema, TypeAdapter):
                return schema.validate_python(payload)
            return schema.model_validate(payload)
        except PydanticValidationError as exc:
            raise WeatherProviderError(error_message) from exc

    def _build_geocoding_query(self, query: CityQuery) -> str:
        parts = [query.city]
        if query.state:
            parts.append(query.state)
        if query.country:
            parts.append(query.country)
        return ",".join(parts)

    def _matches_geolocation_filters(self, location: GeocodingLocationPayload, query: CityQuery) -> bool:
        if query.country and location.country.upper() != query.country.upper():
            return False
        if query.state is None:
            return True
        return self._normalize(location.state) == self._normalize(query.state)

    def _normalize(self, value: str | None) -> str:
        normalized_spaces = " ".join((value or "").split())
        normalized_case = normalized_spaces.casefold()
        without_accents = unicodedata.normalize("NFKD", normalized_case)
        return "".join(char for char in without_accents if not unicodedata.combining(char))
