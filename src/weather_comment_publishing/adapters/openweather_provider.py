from __future__ import annotations

from dataclasses import dataclass
import unicodedata

from src.integrations.openweather import OpenWeather
from src.integrations.openweather.exceptions import (
    OpenWeatherContractError,
    OpenWeatherNotFoundError,
    OpenWeatherRequestError,
)
from src.shared.exceptions import (
    LocationAmbiguousError,
    LocationNotFoundError,
    ProviderContractError,
    WeatherProviderError,
)
from src.weather_comment_publishing.protocols import WeatherProviderPort
from src.weather_comment_publishing.types import CityQuery, Coordinates, CurrentWeather, ForecastEntry, ResolvedLocation


@dataclass(frozen=True, slots=True)
class OpenWeatherProviderAdapter(WeatherProviderPort):
    sdk_client: OpenWeather

    async def resolve_city(self, query: CityQuery) -> ResolvedLocation:
        MAX_LOCATIONS_LIMIT = 5
        try:
            if query.zipcode:
                return await self.sdk_client.geocode_zip(
                    zipcode=query.zipcode,
                    country_code=query.country or "",
                )

            locations = await self.sdk_client.geocode_direct(
                city=query.city or "",
                state=query.state,
                country_code=query.country,
                limit=MAX_LOCATIONS_LIMIT,
            )
        except OpenWeatherNotFoundError as exc:
            raise LocationNotFoundError(str(exc)) from exc
        except OpenWeatherContractError as exc:
            raise ProviderContractError(str(exc)) from exc
        except OpenWeatherRequestError as exc:
            raise WeatherProviderError(str(exc)) from exc

        filtered_locations = [location for location in locations if self._matches_geolocation_filters(location, query)]
        if not filtered_locations:
            raise LocationNotFoundError("Location not found.")
        if len(filtered_locations) > 1:
            raise LocationAmbiguousError("Location is ambiguous.")
        return filtered_locations[0]

    async def get_current_weather(self, coordinates: Coordinates) -> CurrentWeather:
        try:
            return await self.sdk_client.read_current_weather(coordinates)
        except OpenWeatherContractError as exc:
            raise ProviderContractError(str(exc)) from exc
        except OpenWeatherRequestError as exc:
            raise WeatherProviderError(str(exc)) from exc

    async def get_five_day_forecast(self, coordinates: Coordinates) -> list[ForecastEntry]:
        try:
            return await self.sdk_client.read_five_day_forecast(coordinates)
        except OpenWeatherContractError as exc:
            raise ProviderContractError(str(exc)) from exc
        except OpenWeatherRequestError as exc:
            raise WeatherProviderError(str(exc)) from exc

    def _matches_geolocation_filters(self, location: ResolvedLocation, query: CityQuery) -> bool:
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
