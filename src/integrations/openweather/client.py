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

from src.weather_comment_publishing.protocols import WeatherProviderPort


ModelT = TypeVar("ModelT", bound=BaseModel)
ParsedT = TypeVar("ParsedT")


@dataclass(frozen=True, slots=True)
class OpenWeatherApiClient(WeatherProviderPort):
    api_key: str
    base_url: str
    language: str
    units: str
    timeout_seconds: float
    mapper: OpenWeatherMapper = field(default_factory=OpenWeatherMapper)

    async def resolve_city(self, query: CityQuery) -> ResolvedLocation:
        if query.zipcode:
            return await self._resolve_by_zipcode(query)

        if query.city:
            return await self._resolve_by_name(query)

        raise LocationNotFoundError("City name or zipcode+country required for location search.")

    async def _resolve_by_zipcode(self, query: CityQuery) -> ResolvedLocation:
        zipcode = query.zipcode
        country_code = query.country
        if not zipcode or not country_code:
            raise LocationNotFoundError("Zipcode and country code required for zip search.")

        normalized_zipcode = self._normalize_zipcode_for_provider(zipcode, country_code)
        response = await self._request_json(
            endpoint="/geo/1.0/zip",
            params={
                "zip": f"{normalized_zipcode},{country_code}",
                "appid": self.api_key,
            },
            error_message="Failed to resolve location by zipcode from OpenWeather.",
        )
        if not response or not isinstance(response, dict):
            raise LocationNotFoundError("Location not found by zipcode.")
        try:
            location_payload = GeocodingLocationPayload.model_validate(response)
        except Exception:
            raise LocationNotFoundError("Location not found by zipcode.")
        return self.mapper.to_resolved_location(location_payload)

    async def _resolve_by_name(self, query: CityQuery) -> ResolvedLocation:
        response = await self._request_json(
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
            response,
            error_message="Invalid OpenWeather geocoding payload.",
        )
        filtered_locations = [loc for loc in locations if self._matches_geolocation_filters(loc, query)]
        if not filtered_locations:
            raise LocationNotFoundError("Location not found.")
        if len(filtered_locations) > 1:
            raise LocationAmbiguousError("Location is ambiguous.")
        return self.mapper.to_resolved_location(filtered_locations[0])

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

    def _normalize_zipcode_for_provider(self, zipcode: str, country_code: str) -> str:
        if country_code.upper() == "BR":
            digits = "".join(char for char in zipcode if char.isdigit())
            if len(digits) == 8:
                return f"{digits[:5]}-{digits[5:]}"
        return zipcode.strip()
