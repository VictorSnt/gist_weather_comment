from __future__ import annotations


class AppError(Exception):
    def __init__(self, message: str, *, field: str | None = None) -> None:
        super().__init__(message)
        self.field = field


class GistNotFoundError(AppError):
    pass


class GistAccessDeniedError(AppError):
    pass


class GistCommentNotAllowedError(AppError):
    pass


class GitHubGistIntegrationError(AppError):
    pass


class LocationNotFoundError(AppError):
    pass


class LocationAmbiguousError(AppError):
    pass


class WeatherProviderError(AppError):
    pass


class ProviderContractError(AppError):
    pass


class ConfigError(AppError):
    pass
