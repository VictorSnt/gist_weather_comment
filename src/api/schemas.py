from __future__ import annotations

from pydantic import BaseModel


class PublishWeatherCommentRequest(BaseModel):
    gist_id: str
    city: str
    state: str | None = None
    country: str | None = None


class PublishWeatherCommentResponse(BaseModel):
    gist_id: str
    comment_id: int
    comment: str


class ErrorResponse(BaseModel):
    error_code: str
    message: str
    field: str | None = None
