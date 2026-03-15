from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


def _normalize_optional_non_empty(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        raise ValueError("campo não pode ser string vazia")
    return stripped


def _normalize_country(value: str) -> str:
    normalized = value.strip().upper()
    if len(normalized) != 2:
        raise ValueError("country deve ter exatamente 2 caracteres")
    return normalized


def _normalize_zipcode_for_country(zipcode: str, country: str) -> str:
    normalized_zipcode = zipcode.strip()
    if country == "BR":
        digits = "".join(char for char in normalized_zipcode if char.isdigit())
        if len(digits) != 8:
            raise ValueError("zipcode BR deve conter 8 dígitos")
        return f"{digits[:5]}-{digits[5:]}"
    return normalized_zipcode


class CityLocationRequest(BaseModel):
    kind: Literal["city"]
    city: str
    state: str | None = None
    country: str | None = None

    @field_validator("city", "state")
    @classmethod
    def normalize_non_empty_fields(cls, value: str | None) -> str | None:
        return _normalize_optional_non_empty(value)

    @field_validator("country")
    @classmethod
    def validate_country(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _normalize_country(value)


class ZipcodeLocationRequest(BaseModel):
    kind: Literal["zipcode"]
    zipcode: str
    country: str

    @field_validator("zipcode")
    @classmethod
    def validate_zipcode(cls, value: str) -> str:
        normalized = _normalize_optional_non_empty(value)
        if normalized is None:
            raise ValueError("campo não pode ser string vazia")
        return normalized

    @field_validator("country")
    @classmethod
    def validate_country(cls, value: str) -> str:
        return _normalize_country(value)

    @model_validator(mode="after")
    def normalize_zipcode(self) -> "ZipcodeLocationRequest":
        self.zipcode = _normalize_zipcode_for_country(self.zipcode, self.country)
        return self


LocationRequest = Annotated[CityLocationRequest | ZipcodeLocationRequest, Field(discriminator="kind")]


class PublishWeatherCommentRequest(BaseModel):
    """Requisição para publicar comentário meteorológico."""

    gist_id: str = Field(..., min_length=1)
    location: LocationRequest

    @field_validator("gist_id")
    @classmethod
    def not_empty_if_provided(cls, value: str) -> str:
        normalized = _normalize_optional_non_empty(value)
        if normalized is None:
            raise ValueError("campo não pode ser string vazia")
        return normalized


class PublishWeatherCommentResponse(BaseModel):
    gist_id: str
    comment_id: int
    comment: str


class ErrorResponse(BaseModel):
    error_code: str
    message: str
    field: str | None = None
