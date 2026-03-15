from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from typing_extensions import Annotated

from src.integrations.openweather.types import (
    LocationQuery,
    ResolvedLocation,
)

NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
CityQuery = LocationQuery


class PublishedWeatherComment(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    gist_id: NonEmptyStr
    comment_id: int = Field(gt=0)
    location: ResolvedLocation
    comment: NonEmptyStr
