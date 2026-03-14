from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter


class OpenWeatherPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")


class GeocodingLocationPayload(OpenWeatherPayload):
    name: str
    country: str
    lat: float
    lon: float
    state: str | None = None


class MainPayload(OpenWeatherPayload):
    temp: float


class WeatherConditionPayload(OpenWeatherPayload):
    id: int
    main: str
    description: str
    icon: str


class CurrentWeatherPayload(OpenWeatherPayload):
    dt: int
    timezone: int | None = None
    main: MainPayload
    weather: list[WeatherConditionPayload] = Field(min_length=1)


class ForecastItemPayload(OpenWeatherPayload):
    dt: int
    main: MainPayload
    weather: list[WeatherConditionPayload] = Field(min_length=1)


class ForecastCityPayload(OpenWeatherPayload):
    timezone: int | None = None


class ForecastPayload(OpenWeatherPayload):
    timezone: int | None = None
    city: ForecastCityPayload | None = None
    list: list[ForecastItemPayload]


GEOCODING_LOCATIONS = TypeAdapter(list[GeocodingLocationPayload])
