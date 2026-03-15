from __future__ import annotations
import logging
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
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
    ProviderContractError,
    ValidationError,
    WeatherProviderError,
)

logger = logging.getLogger(__name__)


def _log_exception_with_cause(message: str, exception: Exception) -> None:
    cause = exception.__cause__
    if cause is None:
        logger.error(message, exc_info=(type(exception), exception, exception.__traceback__))
        return

    logger.error(
        "%s | cause=%s: %s",
        message,
        type(cause).__name__,
        str(cause),
        exc_info=(type(exception), exception, exception.__traceback__),
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ValidationError)
    async def validation_error_handler(_: Request, exception: ValidationError) -> JSONResponse:
        return _json_error(400, "invalid_request", str(exception), field=exception.field)

    @app.exception_handler(RequestValidationError)
    async def request_validation_error_handler(_: Request, exception: RequestValidationError) -> JSONResponse:
        first_error = exception.errors()[0] if exception.errors() else None
        field = str(first_error["loc"][-1]) if first_error and first_error.get("loc") else None
        message = str(first_error["msg"]) if first_error else str(exception)
        return _json_error(422, "invalid_request", message, field=field)

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
        _log_exception_with_cause(f"Weather provider error: {exception}", exception)
        return _json_error(502, "upstream_failure", str(exception))

    @app.exception_handler(ProviderContractError)
    async def provider_contract_error_handler(_: Request, exception: ProviderContractError) -> JSONResponse:
        _log_exception_with_cause(f"Provider contract error: {exception}", exception)
        return _json_error(500, "integration_contract_error", str(exception))

    @app.exception_handler(GitHubGistIntegrationError)
    async def github_gist_integration_error_handler(_: Request, exception: GitHubGistIntegrationError) -> JSONResponse:
        _log_exception_with_cause(f"GitHub Gist integration error: {exception}", exception)
        return _json_error(502, "upstream_failure", str(exception))

    @app.exception_handler(GitHubClientError)
    async def github_client_error_handler(_: Request, exception: GitHubClientError) -> JSONResponse:
        _log_exception_with_cause(f"GitHub client error: {exception}", exception)
        return _json_error(502, "upstream_failure", str(exception))

    @app.exception_handler(ConfigError)
    async def config_error_handler(_: Request, exception: ConfigError) -> JSONResponse:
        _log_exception_with_cause(f"Configuration error: {exception}", exception)
        return _json_error(500, "configuration_error", str(exception), field=exception.field)

    @app.exception_handler(Exception)
    async def unexpected_error_handler(_: Request, __: Exception) -> JSONResponse:
        _log_exception_with_cause(f"Unexpected error: {__}", __)
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
