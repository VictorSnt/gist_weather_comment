from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError

from src.shared.exceptions import (
    ConfigError,
    GistAccessDeniedError,
    GistCommentNotAllowedError,
    GitHubGistIntegrationError,
    GistNotFoundError,
    GitHubClientError,
    LocationAmbiguousError,
    LocationNotFoundError,
    ValidationError,
    WeatherProviderError,
)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ValidationError)
    async def validation_error_handler(_: Request, exception: ValidationError) -> JSONResponse:
        return _json_error(400, "invalid_request", str(exception), field=exception.field)

    @app.exception_handler(PydanticValidationError)
    async def pydantic_validation_error_handler(_: Request, exception: PydanticValidationError) -> JSONResponse:
        first_error = exception.errors()[0] if exception.errors() else None
        field = str(first_error["loc"][-1]) if first_error and first_error.get("loc") else None
        message = str(first_error["msg"]) if first_error else str(exception)
        return _json_error(400, "invalid_request", message, field=field)

    @app.exception_handler(LocationNotFoundError)
    async def location_not_found_handler(_: Request, exception: LocationNotFoundError) -> JSONResponse:
        return _json_error(404, "location_not_found", str(exception))

    @app.exception_handler(LocationAmbiguousError)
    async def location_ambiguous_handler(_: Request, exception: LocationAmbiguousError) -> JSONResponse:
        return _json_error(409, "location_ambiguous", str(exception))

    @app.exception_handler(GistNotFoundError)
    async def gist_not_found_handler(_: Request, exception: GistNotFoundError) -> JSONResponse:
        return _json_error(404, "gist_not_found", str(exception))

    @app.exception_handler(GistAccessDeniedError)
    async def gist_access_denied_handler(_: Request, exception: GistAccessDeniedError) -> JSONResponse:
        return _json_error(403, "gist_access_denied", str(exception))

    @app.exception_handler(GistCommentNotAllowedError)
    async def gist_comment_not_allowed_handler(_: Request, exception: GistCommentNotAllowedError) -> JSONResponse:
        return _json_error(403, "gist_comment_not_allowed", str(exception))

    @app.exception_handler(WeatherProviderError)
    async def weather_provider_error_handler(_: Request, exception: WeatherProviderError) -> JSONResponse:
        return _json_error(502, "upstream_failure", str(exception))

    @app.exception_handler(GitHubGistIntegrationError)
    async def github_gist_integration_error_handler(_: Request, exception: GitHubGistIntegrationError) -> JSONResponse:
        return _json_error(502, "upstream_failure", str(exception))

    @app.exception_handler(GitHubClientError)
    async def github_client_error_handler(_: Request, exception: GitHubClientError) -> JSONResponse:
        return _json_error(502, "upstream_failure", str(exception))

    @app.exception_handler(ConfigError)
    async def config_error_handler(_: Request, exception: ConfigError) -> JSONResponse:
        return _json_error(500, "configuration_error", str(exception), field=exception.field)

    @app.exception_handler(Exception)
    async def unexpected_error_handler(_: Request, __: Exception) -> JSONResponse:
        return _json_error(500, "internal_error", "Internal server error.")


def _json_error(status_code: int, error_code: str, message: str, *, field: str | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error_code": error_code,
            "message": message,
            "field": field,
        },
    )
