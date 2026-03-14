from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator
from typing_extensions import Annotated

NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
IsoCountryCode = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=2, max_length=2, pattern=r"^[A-Z]{2}$"),
]


class Coordinates(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class CityQuery(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    city: NonEmptyStr
    state: str | None = None
    country: IsoCountryCode | None = None
    zipcode: str | None = None

    @field_validator("state", mode="before")
    @classmethod
    def normalize_and_validate_state(cls, value: object) -> object:
        if value is None:
            return None

        if isinstance(value, str):
            stripped = " ".join(value.split())
            if not stripped:
                return None

            if len(stripped) <= 2:
                raise ValueError("state must be informed with the full state name, not abbreviation")

            return stripped

        return value

    @field_validator("country", mode="before")
    @classmethod
    def normalize_country(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped.upper() if stripped else stripped
        return value


class ResolvedLocation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: NonEmptyStr
    state: str | None
    country: IsoCountryCode
    coordinates: Coordinates

    @field_validator("state", mode="before")
    @classmethod
    def empty_state_as_none(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value

    @field_validator("country", mode="before")
    @classmethod
    def normalize_country(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().upper()
        return value


class WeatherCondition(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    code: int
    group: NonEmptyStr
    description: NonEmptyStr
    icon: NonEmptyStr


class CurrentWeather(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    temperature_celsius: float
    condition: WeatherCondition
    observed_at: datetime

    @field_validator("observed_at")
    @classmethod
    def observed_at_must_be_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("Observed at must be timezone-aware.")
        return value

    @property
    def current_condition(self) -> str:
        return self.condition.description



class ForecastEntry(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    forecasted_at: datetime
    temperature_celsius: float

    @field_validator("forecasted_at")
    @classmethod
    def forecasted_at_must_be_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("Forecasted at must be timezone-aware.")
        return value


class PublishedWeatherComment(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    gist_id: NonEmptyStr
    comment_id: int = Field(gt=0)
    location: ResolvedLocation
    comment: NonEmptyStr
