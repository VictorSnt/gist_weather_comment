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
    kind: Literal["city"] = Field(description="Tipo da busca de localidade.")
    city: str = Field(description="Nome da cidade.", examples=["Sao Paulo"])
    state: str | None = Field(
        default=None,
        description="Nome completo do estado/província (sem sigla).",
        examples=["Sao Paulo"],
    )
    country: str | None = Field(
        default=None,
        description="Código ISO-3166 alfa-2.",
        examples=["BR"],
    )

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
    kind: Literal["zipcode"] = Field(description="Tipo da busca de localidade.")
    zipcode: str = Field(
        description="CEP/código postal. Para BR, aceita com ou sem hífen e normaliza para 12345-678.",
        examples=["01001-000", "01001000"],
    )
    country: str = Field(description="Código ISO-3166 alfa-2.", examples=["BR"])

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

    gist_id: str = Field(..., min_length=1, description="ID do Gist que receberá o comentário.")
    location: LocationRequest = Field(description="Objeto discriminado por 'kind': city ou zipcode.")

    @field_validator("gist_id")
    @classmethod
    def not_empty_if_provided(cls, value: str) -> str:
        normalized = _normalize_optional_non_empty(value)
        if normalized is None:
            raise ValueError("campo não pode ser string vazia")
        return normalized


class PublishWeatherCommentResponse(BaseModel):
    gist_id: str = Field(description="ID do Gist comentado.")
    comment_id: int = Field(description="ID do comentário criado no Gist.")
    comment: str = Field(description="Texto publicado no comentário.")


class ErrorResponse(BaseModel):
    error_code: str = Field(description="Código estável de erro.")
    message: str = Field(description="Mensagem de erro para diagnóstico.")
    field: str | None = Field(default=None, description="Campo relacionado ao erro, quando aplicável.")
