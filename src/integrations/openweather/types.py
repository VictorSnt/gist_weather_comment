from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator
from typing_extensions import Annotated

NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
IsoCountryCode = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=2, max_length=2, pattern=r"^[A-Z]{2}$"),
]


def _normalize_zipcode_for_country(zipcode: str, country: str | None) -> str:
    normalized_zipcode = zipcode.strip()
    if country == "BR":
        digits = "".join(char for char in normalized_zipcode if char.isdigit())
        if len(digits) != 8:
            raise ValueError("zipcode BR must contain 8 digits")
        return f"{digits[:5]}-{digits[5:]}"
    return normalized_zipcode


class Coordinates(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class LocationQuery(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    city: NonEmptyStr | None = None
    state: str | None = None
    country: IsoCountryCode | None = None
    zipcode: str | None = None

    @field_validator("city", "zipcode", mode="before")
    @classmethod
    def empty_strings_as_none(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value

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

    @model_validator(mode="before")
    @classmethod
    def normalize_zipcode_for_country(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data

        zipcode = data.get("zipcode")
        if not isinstance(zipcode, str):
            return data

        country = data.get("country")
        normalized_country = country.strip().upper() if isinstance(country, str) else country
        normalized_zipcode = _normalize_zipcode_for_country(zipcode, normalized_country)
        if normalized_zipcode == zipcode:
            return data

        updated_data = dict(data)
        updated_data["zipcode"] = normalized_zipcode
        return updated_data

    @model_validator(mode="after")
    def validate_location_rules(self) -> LocationQuery:
        if self.city and self.zipcode:
            raise ValueError("provide either city or zipcode, not both")

        if self.zipcode and not self.country:
            raise ValueError("zipcode requires country")

        if self.state and not self.city:
            raise ValueError("state requires city")

        if not self.city and not self.zipcode:
            raise ValueError("city or zipcode is required")

        return self


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
