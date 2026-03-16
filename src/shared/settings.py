from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from src.shared.exceptions import ConfigError


@dataclass(frozen=True, slots=True)
class Settings:
    openweather_api_key: str
    openweather_base_url: str
    openweather_language: str
    github_token: str
    http_timeout_seconds: float
    forecast_days_limit: int

    @classmethod
    def from_env(cls, environ: Mapping[str, str]) -> "Settings":
        return cls(
            openweather_api_key=cls._required_env(environ, "OPENWEATHER_API_KEY"),
            openweather_base_url=cls._optional_env(environ, "OPENWEATHER_BASE_URL", "https://api.openweathermap.org"),
            openweather_language=cls._optional_env(environ, "OPENWEATHER_LANGUAGE", "pt_br"),
            github_token=cls._required_env(environ, "GITHUB_TOKEN"),
            http_timeout_seconds=cls._optional_float(environ, "HTTP_CLIENT_TIMEOUT_SECONDS", 10.0),
            forecast_days_limit=cls._optional_int(environ, "FORECAST_DAYS_LIMIT", 5),
        )

    @staticmethod
    def _required_env(environ: Mapping[str, str], key: str) -> str:
        value = environ.get(key)
        if value is None or value.strip() == "":
            raise ConfigError("Missing required environment variable.", field=key)
        return value.strip()

    @staticmethod
    def _optional_env(environ: Mapping[str, str], key: str, default: str) -> str:
        value = environ.get(key)
        if value is None or value.strip() == "":
            return default
        return value.strip()

    @staticmethod
    def _optional_int(environ: Mapping[str, str], key: str, default: int) -> int:
        value = environ.get(key)
        if value is None or value.strip() == "":
            return default
        try:
            return int(value.strip())
        except ValueError as exc:
            raise ConfigError("Environment variable must be an integer.", field=key) from exc

    @staticmethod
    def _optional_float(environ: Mapping[str, str], key: str, default: float) -> float:
        value = environ.get(key)
        if value is None or value.strip() == "":
            return default
        try:
            return float(value.strip())
        except ValueError as exc:
            raise ConfigError("Environment variable must be a number.", field=key) from exc
