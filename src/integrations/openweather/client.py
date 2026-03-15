from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, TypeVar, overload

import httpx
from pydantic import BaseModel, TypeAdapter, ValidationError as PydanticValidationError

from src.integrations.openweather.exceptions import (
    OpenWeatherContractError,
    OpenWeatherNotFoundError,
    OpenWeatherRequestError,
)
from src.integrations.openweather.mapper import OpenWeatherMapper
from src.integrations.openweather.schemas import (
    CurrentWeatherPayload,
    ForecastPayload,
    GEOCODING_LOCATIONS,
    GeocodingLocationPayload,
)
from src.integrations.openweather.types import Coordinates, CurrentWeather, ForecastEntry, ResolvedLocation


ModelT = TypeVar("ModelT", bound=BaseModel)
ParsedT = TypeVar("ParsedT")


@dataclass(frozen=True, slots=True)
class OpenWeatherApiClient:
    """OpenWeather HTTP SDK client."""

    api_key: str
    base_url: str
    language: str
    units: str
    timeout_seconds: float
    mapper: OpenWeatherMapper = field(default_factory=OpenWeatherMapper)

    async def geocode_zip(self, *, zipcode: str, country_code: str) -> ResolvedLocation:
        """Resolve a location by ZIP/postal code using `/geo/1.0/zip`."""
        normalized_zipcode = self._normalize_zipcode_for_provider(zipcode, country_code)
        if not normalized_zipcode or not country_code:
            raise OpenWeatherNotFoundError("Zipcode and country code required for zip search.")

        response = await self._request_json(
            endpoint="/geo/1.0/zip",
            params={
                "zip": f"{normalized_zipcode},{country_code}",
                "appid": self.api_key,
            },
            error_message="Failed to resolve location by zipcode from OpenWeather.",
            not_found_message="Location not found by zipcode.",
        )
        if not response or not isinstance(response, dict):
            raise OpenWeatherNotFoundError("Location not found by zipcode.")
        try:
            location_payload = GeocodingLocationPayload.model_validate(response)
        except Exception:
            raise OpenWeatherNotFoundError("Location not found by zipcode.")
        return self.mapper.to_resolved_location(location_payload)

    async def geocode_direct(
        self,
        *,
        city: str,
        state: str | None = None,
        country_code: str | None = None,
        limit: int = 5,
    ) -> list[ResolvedLocation]:
        """Search locations by name using `/geo/1.0/direct`."""
        geocoding_query = self._build_geocoding_query(
            city=city,
            state=state,
            country_code=country_code,
        )
        response = await self._request_json(
            endpoint="/geo/1.0/direct",
            params={
                "q": geocoding_query,
                "limit": str(limit),
                "appid": self.api_key,
            },
            error_message="Failed to resolve location from OpenWeather.",
        )
        locations = self._parse_payload(
            GEOCODING_LOCATIONS,
            response,
            error_message="Invalid OpenWeather geocoding payload.",
        )
        return [self.mapper.to_resolved_location(location) for location in locations]

    async def read_current_weather(self, coordinates: Coordinates) -> CurrentWeather:
        """Read current weather from `/data/2.5/weather`."""
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

    async def read_five_day_forecast(self, coordinates: Coordinates) -> list[ForecastEntry]:
        """Read five-day/3-hour forecast from `/data/2.5/forecast`."""
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
        not_found_message: str | None = None,
    ) -> object:
        url = f"{self.base_url.rstrip('/')}{endpoint}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                if not_found_message and self._is_openweather_not_found_response(exc.response):
                    raise OpenWeatherNotFoundError(not_found_message) from exc
                raise OpenWeatherContractError(
                    f"Unexpected 404 from OpenWeather [endpoint={endpoint}]",
                ) from exc
            raise OpenWeatherRequestError(
                f"{error_message} [endpoint={endpoint}, status={exc.response.status_code}]",
            ) from exc
        except httpx.HTTPError as exc:
            raise OpenWeatherRequestError(f"{error_message} [endpoint={endpoint}]") from exc

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
            raise OpenWeatherRequestError(error_message) from exc

    def _build_geocoding_query(self, *, city: str, state: str | None, country_code: str | None) -> str:
        normalized_city = city.strip()
        if not normalized_city:
            raise OpenWeatherNotFoundError("City name required for direct geocoding.")

        parts = [normalized_city]
        if state:
            parts.append(state.strip())
        if country_code:
            parts.append(country_code.strip())
        return ",".join(part for part in parts if part)

    def _normalize_zipcode_for_provider(self, zipcode: str, country_code: str) -> str:
        if country_code.upper() == "BR":
            return self._normalize_br_zipcode(zipcode)
        return zipcode.strip()

    def _is_openweather_not_found_response(self, response: httpx.Response) -> bool:
        try:
            payload = response.json()
        except ValueError:
            return False

        if not isinstance(payload, dict):
            return False

        cod = str(payload.get("cod", "")).strip()
        message = str(payload.get("message", "")).strip().lower()
        return cod == "404" and "not found" in message

    def _normalize_br_zipcode(self, zipcode: str) -> str:
        digits = "".join(char for char in zipcode if char.isdigit())
        if len(digits) == 8:
            return f"{digits[:5]}-{digits[5:]}"
        return zipcode.strip()
