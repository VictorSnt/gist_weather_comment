from __future__ import annotations


class OpenWeatherSdkError(Exception):
    """Base exception for OpenWeather SDK failures."""


class OpenWeatherNotFoundError(OpenWeatherSdkError):
    """Raised when a location cannot be found in OpenWeather."""


class OpenWeatherRequestError(OpenWeatherSdkError):
    """Raised when OpenWeather request fails due to transport/upstream status errors."""


class OpenWeatherContractError(OpenWeatherSdkError):
    """Raised when OpenWeather response breaks expected provider contract."""
