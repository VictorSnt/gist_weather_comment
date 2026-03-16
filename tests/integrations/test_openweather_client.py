from __future__ import annotations

import httpx
import pytest

from src.integrations.openweather import OpenWeather
from src.integrations.openweather.exceptions import (
    OpenWeatherContractError,
    OpenWeatherNotFoundError,
    OpenWeatherRequestError,
)
from src.integrations.openweather.types import Coordinates


class FakeAsyncClient:
    def __init__(
        self,
        *,
        response: httpx.Response | None = None,
        request_error: Exception | None = None,
    ) -> None:
        self.response = response
        self.request_error = request_error

    async def __aenter__(self) -> "FakeAsyncClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False

    async def get(self, url: str, params: dict[str, str]) -> httpx.Response:
        if self.request_error is not None:
            raise self.request_error
        assert self.response is not None
        return self.response


def _response(status_code: int, payload: object) -> httpx.Response:
    request = httpx.Request("GET", "https://api.openweathermap.org")
    return httpx.Response(status_code=status_code, json=payload, request=request)


def _client() -> OpenWeather:
    return OpenWeather(
        api_key="test-key",
        base_url="https://api.openweathermap.org",
        language="pt_br",
        units="metric",
        timeout_seconds=10.0,
    )


def _patch_client(monkeypatch: pytest.MonkeyPatch, fake: FakeAsyncClient) -> None:
    monkeypatch.setattr(httpx, "AsyncClient", lambda *args, **kwargs: fake)


@pytest.mark.asyncio
async def test_geocode_direct_raises_openweather_request_error_on_network_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request_error = httpx.RequestError(
        "boom",
        request=httpx.Request("GET", "https://api.openweathermap.org"),
    )
    fake = FakeAsyncClient(request_error=request_error)
    _patch_client(monkeypatch, fake)

    with pytest.raises(OpenWeatherRequestError, match="Failed to resolve location"):
        await _client().geocode_direct(city="Sao Paulo")


@pytest.mark.asyncio
async def test_geocode_zip_raises_openweather_not_found_when_provider_returns_not_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakeAsyncClient(
        response=_response(404, {"cod": "404", "message": "not found"})
    )
    _patch_client(monkeypatch, fake)

    with pytest.raises(OpenWeatherNotFoundError, match="Location not found by zipcode"):
        await _client().geocode_zip(zipcode="01001-000", country_code="BR")


@pytest.mark.asyncio
async def test_geocode_direct_raises_openweather_contract_error_on_unexpected_404(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakeAsyncClient(
        response=_response(404, {"cod": "404", "message": "oops"})
    )
    _patch_client(monkeypatch, fake)

    with pytest.raises(OpenWeatherContractError, match="Unexpected 404 from OpenWeather"):
        await _client().geocode_direct(city="Sao Paulo")


@pytest.mark.asyncio
async def test_read_current_weather_raises_openweather_contract_error_on_invalid_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakeAsyncClient(response=_response(200, {"bad": "payload"}))
    _patch_client(monkeypatch, fake)

    coords = Coordinates(latitude=-23.55, longitude=-46.63)

    with pytest.raises(
        OpenWeatherContractError,
        match="Invalid OpenWeather current weather payload",
    ):
        await _client().read_current_weather(coordinates=coords)


@pytest.mark.asyncio
async def test_read_five_day_forecast_raises_openweather_contract_error_on_invalid_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakeAsyncClient(response=_response(200, {"bad": "payload"}))
    _patch_client(monkeypatch, fake)

    coords = Coordinates(latitude=-23.55, longitude=-46.63)

    with pytest.raises(
        OpenWeatherContractError,
        match="Invalid OpenWeather forecast payload",
    ):
        await _client().read_five_day_forecast(coordinates=coords)