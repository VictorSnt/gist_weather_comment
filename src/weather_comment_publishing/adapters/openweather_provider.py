from __future__ import annotations

from dataclasses import dataclass
import unicodedata

from src.integrations.openweather import OpenWeather
from src.integrations.openweather import (
    Coordinates as OpenWeatherCoordinates,
    ResolvedLocation as OpenWeatherResolvedLocation,
    CurrentWeather as OpenWeatherCurrentWeather,
    ForecastEntry as OpenWeatherForecastEntry,
)
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
from src.weather_comment_publishing.types import (
    CityQuery,
    Coordinates,
    CurrentWeather,
    ForecastEntry,
    ResolvedLocation,
    WeatherCondition,
)

MAX_GEOCODING_RESULTS = 5


@dataclass(frozen=True, slots=True)
class OpenWeatherProviderAdapter(WeatherProviderPort):
    sdk_client: OpenWeather

    async def resolve_city(self, query: CityQuery) -> ResolvedLocation:
        try:
            if query.zipcode:
                location = await self.sdk_client.geocode_zip(
                    zipcode=query.zipcode,
                    country_code=query.country or "",
                )
                return self._to_domain_location(location)

            # OpenWeather direct geocoding não funciona bem com country_code,
            # então aplicamos o filtro manualmente depois.
            locations = await self.sdk_client.geocode_direct(
                city=query.city,
                state=query.state,
                country_code=None,
                limit=MAX_GEOCODING_RESULTS,
            )
        except OpenWeatherNotFoundError as exc:
            raise LocationNotFoundError("Location not found.") from exc
        except OpenWeatherContractError as exc:
            raise ProviderContractError(str(exc)) from exc
        except OpenWeatherRequestError as exc:
            raise WeatherProviderError(str(exc)) from exc

        matching_locations = [
            location
            for location in locations
            if self._matches_location_filters(location, query)
        ]

        selected_location = self._select_single_location(locations=matching_locations, query=query)
        return self._to_domain_location(location=selected_location)

    async def get_current_weather(self, coordinates: Coordinates) -> CurrentWeather:
        try:
            weather = await self.sdk_client.read_current_weather(
                OpenWeatherCoordinates(
                    latitude=coordinates.latitude,
                    longitude=coordinates.longitude,
                )
            )
            return self._to_domain_current_weather(weather)
        except OpenWeatherContractError as exc:
            raise ProviderContractError(str(exc)) from exc
        except OpenWeatherRequestError as exc:
            raise WeatherProviderError(str(exc)) from exc

    async def get_five_day_forecast(
        self,
        coordinates: Coordinates,
    ) -> list[ForecastEntry]:
        try:
            entries = await self.sdk_client.read_five_day_forecast(
                OpenWeatherCoordinates(
                    latitude=coordinates.latitude,
                    longitude=coordinates.longitude,
                )
            )
            return self._to_domain_forecast(entries)
        except OpenWeatherContractError as exc:
            raise ProviderContractError(str(exc)) from exc
        except OpenWeatherRequestError as exc:
            raise WeatherProviderError(str(exc)) from exc


    def _matches_location_filters(
        self,
        location: OpenWeatherResolvedLocation,
        query: CityQuery,
    ) -> bool:
        if query.country and location.country.upper() != query.country.upper():
            return False

        if query.city and self._normalize_text(location.name) != self._normalize_text(query.city):
            return False

        if query.state and self._normalize_text(location.state) != self._normalize_text(query.state):
            return False

        return True
    
    def _select_single_location(
        self,
        locations: list[OpenWeatherResolvedLocation],
        query: CityQuery,
    ) -> OpenWeatherResolvedLocation:
        
        if not locations:
            raise LocationNotFoundError("Location not found.")

        if len(locations) == 1:
            return locations[0]

        has_all_filters = bool(query.city and query.state and query.country)
        if not has_all_filters:
            raise LocationAmbiguousError("Location is ambiguous.")

        raise WeatherProviderError("Location is ambiguous after applying all filters.")

    @staticmethod
    def _normalize_text(value: str | None) -> str:
        normalized_spaces = " ".join((value or "").split())
        normalized_case = normalized_spaces.casefold()
        without_accents = unicodedata.normalize("NFKD", normalized_case)
        return "".join(
            char for char in without_accents if not unicodedata.combining(char)
        )

    @staticmethod
    def _to_domain_location(
        location: OpenWeatherResolvedLocation,
    ) -> ResolvedLocation:
        return ResolvedLocation(
            name=location.name,
            state=location.state,
            country=location.country,
            coordinates=Coordinates(
                latitude=location.coordinates.latitude,
                longitude=location.coordinates.longitude,
            ),
        )

    @staticmethod
    def _to_domain_current_weather(weather: OpenWeatherCurrentWeather) -> CurrentWeather:
        return CurrentWeather(
            temperature_celsius=weather.temperature_celsius,
            condition=WeatherCondition(
                code=weather.condition.code,
                group=weather.condition.group,
                description=weather.condition.description,
                icon=weather.condition.icon,
            ),
            observed_at=weather.observed_at,
        )
    
    @staticmethod
    def _to_domain_forecast(entries: list[OpenWeatherForecastEntry]) -> list[ForecastEntry]:
        return [
            ForecastEntry(
                forecasted_at=entry.forecasted_at,
                temperature_celsius=entry.temperature_celsius,
            ) for entry in entries
        ]