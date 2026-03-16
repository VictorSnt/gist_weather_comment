from __future__ import annotations

from dataclasses import dataclass
import unicodedata

from src.integrations.openweather import OpenWeather
from src.integrations.openweather import (
    Coordinates as OpenWeatherCoordinates,
    CurrentWeather as OpenWeatherCurrentWeather,
    ForecastEntry as OpenWeatherForecastEntry,
    ResolvedLocation as OpenWeatherResolvedLocation,
    WeatherCondition as OpenWeatherCondition,
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

            locations = await self.sdk_client.geocode_direct(
                city=query.city or "",
                state=query.state,
                country_code=query.country,
                limit=MAX_GEOCODING_RESULTS,
            )
        except OpenWeatherNotFoundError as exc:
            raise LocationNotFoundError("localidade não encontrada") from exc
        except OpenWeatherContractError as exc:
            raise ProviderContractError(str(exc)) from exc
        except OpenWeatherRequestError as exc:
            raise WeatherProviderError(str(exc)) from exc

        filtered_locations = [
            location
            for location in locations
            if self._matches_location_filters(location, query)
        ]

        if not filtered_locations:
            raise LocationNotFoundError("localidade não encontrada")

        if len(filtered_locations) > 1:
            raise LocationAmbiguousError("localidade ambígua")

        return self._to_domain_location(filtered_locations[0])

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
            return [self._to_domain_forecast_entry(entry) for entry in entries]
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

        if query.state is None:
            return True

        return self._normalize_text(location.state) == self._normalize_text(query.state)

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
    def _to_domain_current_weather(
        weather: OpenWeatherCurrentWeather,
    ) -> CurrentWeather:
        return CurrentWeather(
            temperature_celsius=weather.temperature_celsius,
            condition=OpenWeatherProviderAdapter._to_domain_condition(
                weather.condition
            ),
            observed_at=weather.observed_at,
        )

    @staticmethod
    def _to_domain_forecast_entry(
        entry: OpenWeatherForecastEntry,
    ) -> ForecastEntry:
        return ForecastEntry(
            forecasted_at=entry.forecasted_at,
            temperature_celsius=entry.temperature_celsius,
        )

    @staticmethod
    def _to_domain_condition(
        condition: OpenWeatherCondition,
    ) -> WeatherCondition:
        return WeatherCondition(
            code=condition.code,
            group=condition.group,
            description=condition.description,
            icon=condition.icon,
        )