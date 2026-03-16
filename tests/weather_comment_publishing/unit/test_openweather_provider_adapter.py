from __future__ import annotations

import pytest

from src.integrations.openweather.exceptions import (
    OpenWeatherContractError,
    OpenWeatherNotFoundError,
    OpenWeatherRequestError,
)
from src.shared.exceptions import (
    LocationAmbiguousError,
    LocationNotFoundError,
    ProviderContractError,
    WeatherProviderError,
)
from src.weather_comment_publishing.adapters.openweather_provider import OpenWeatherProviderAdapter
from src.weather_comment_publishing.types import CityQuery, Coordinates, ResolvedLocation


class FakeOpenWeather:
    def __init__(self) -> None:
        self.called: list[tuple[str, dict[str, object]]] = []
        self.result_zip: ResolvedLocation | Exception | None = None
        self.result_direct: list[ResolvedLocation] | Exception | None = None

    async def geocode_zip(self, *, zipcode: str, country_code: str) -> ResolvedLocation:
        self.called.append(("geocode_zip", {"zipcode": zipcode, "country_code": country_code}))
        if isinstance(self.result_zip, Exception):
            raise self.result_zip
        assert isinstance(self.result_zip, ResolvedLocation)
        return self.result_zip

    async def geocode_direct(
        self,
        *,
        city: str,
        state: str | None = None,
        country_code: str | None = None,
        limit: int = 5,
    ) -> list[ResolvedLocation]:
        self.called.append(
            (
                "geocode_direct",
                {"city": city, "state": state, "country_code": country_code, "limit": limit},
            )
        )
        if isinstance(self.result_direct, Exception):
            raise self.result_direct
        assert isinstance(self.result_direct, list)
        return self.result_direct


def _location(
    *,
    name: str,
    state: str | None,
    country: str = "BR",
    coordinates: Coordinates | None = None,
) -> ResolvedLocation:
    return ResolvedLocation(
        name=name,
        state=state,
        country=country,
        coordinates=coordinates or Coordinates(latitude=-23.55, longitude=-46.63),
    )


@pytest.mark.asyncio
async def test_resolve_city_uses_geocode_zip_when_zipcode_present() -> None:
    sdk = FakeOpenWeather()
    sdk.result_zip = _location(name="Sao Paulo", state="Sao Paulo")
    adapter = OpenWeatherProviderAdapter(sdk_client=sdk)

    result = await adapter.resolve_city(CityQuery(city=None, state=None, country="BR", zipcode="01001-000"))

    assert result.name == "Sao Paulo"
    assert sdk.called == [
        ("geocode_zip", {"zipcode": "01001-000", "country_code": "BR"}),
    ]


@pytest.mark.asyncio
async def test_resolve_city_uses_geocode_direct_when_city_present() -> None:
    sdk = FakeOpenWeather()
    sdk.result_direct = [_location(name="Sao Paulo", state="Sao Paulo")]
    adapter = OpenWeatherProviderAdapter(sdk_client=sdk)

    result = await adapter.resolve_city(CityQuery(city="Sao Paulo", state="Sao Paulo", country="BR", zipcode=None))

    assert result.name == "Sao Paulo"
    assert sdk.called == [
        ("geocode_direct", {"city": "Sao Paulo", "state": "Sao Paulo", "country_code": None, "limit": 5}),
    ]


@pytest.mark.asyncio
async def test_resolve_city_maps_openweather_not_found_to_location_not_found() -> None:
    sdk = FakeOpenWeather()
    sdk.result_direct = OpenWeatherNotFoundError("Location not found.")
    adapter = OpenWeatherProviderAdapter(sdk_client=sdk)

    with pytest.raises(LocationNotFoundError, match="Location not found."):
        await adapter.resolve_city(CityQuery(city="Sao Paulo", state=None, country="BR", zipcode=None))


@pytest.mark.asyncio
async def test_resolve_city_maps_openweather_contract_error() -> None:
    sdk = FakeOpenWeather()
    sdk.result_direct = OpenWeatherContractError("Invalid payload.")
    adapter = OpenWeatherProviderAdapter(sdk_client=sdk)

    with pytest.raises(ProviderContractError, match="Invalid payload."):
        await adapter.resolve_city(CityQuery(city="Sao Paulo", state=None, country="BR", zipcode=None))


@pytest.mark.asyncio
async def test_resolve_city_maps_openweather_request_error() -> None:
    sdk = FakeOpenWeather()
    sdk.result_direct = OpenWeatherRequestError("Upstream timeout.")
    adapter = OpenWeatherProviderAdapter(sdk_client=sdk)

    with pytest.raises(WeatherProviderError, match="Upstream timeout."):
        await adapter.resolve_city(CityQuery(city="Sao Paulo", state=None, country="BR", zipcode=None))


@pytest.mark.asyncio
async def test_resolve_city_raises_location_not_found_when_state_filter_removes_all_results() -> None:
    sdk = FakeOpenWeather()
    sdk.result_direct = [_location(name="Rio de Janeiro", state="Rio de Janeiro")]
    adapter = OpenWeatherProviderAdapter(sdk_client=sdk)

    with pytest.raises(LocationNotFoundError, match="Location not found."):
        await adapter.resolve_city(CityQuery(city="Sao Paulo", state="Sao Paulo", country="BR", zipcode=None))

@pytest.mark.asyncio
async def test_resolve_city_raises_location_not_found_when_city_filter_removes_all_results() -> None:
    sdk = FakeOpenWeather()
    sdk.result_direct = [_location(name="Campinas", state="Sao Paulo")]
    adapter = OpenWeatherProviderAdapter(sdk_client=sdk)

    with pytest.raises(LocationNotFoundError, match="Location not found."):
        await adapter.resolve_city(CityQuery(city="Sao Paulo", state="Sao Paulo", country="BR", zipcode=None))


@pytest.mark.asyncio
async def test_resolve_city_raises_location_ambiguous_when_multiple_results_match() -> None:
    sdk = FakeOpenWeather()
    sdk.result_direct = [
        _location(name="Sao Paulo", state="Sao Paulo", country="BR"),
        _location(name="Sao Paulo", state="Sao Paulo", country="PT"),
    ]
    adapter = OpenWeatherProviderAdapter(sdk_client=sdk)

    with pytest.raises(LocationAmbiguousError, match="Location is ambiguous."):
        await adapter.resolve_city(CityQuery(city="Sao Paulo", state="Sao Paulo", zipcode=None))

@pytest.mark.asyncio
async def test_resolve_city_raises_weather_provider_error_when_ambiguous_with_all_filters() -> None:
    sdk = FakeOpenWeather()
    sdk.result_direct = [
        _location(name="Sao Paulo", state="Sao Paulo", country="BR"),
        _location(name="Sao Paulo", state="Sao Paulo", country="BR"),
    ]
    adapter = OpenWeatherProviderAdapter(sdk_client=sdk)

    with pytest.raises(WeatherProviderError, match="Location is ambiguous after applying all filters."):
        await adapter.resolve_city(CityQuery(city="Sao Paulo", state="Sao Paulo", country="BR", zipcode=None))

@pytest.mark.asyncio
async def test_resolve_city_state_normalization_ignores_accent_and_case() -> None:
    sdk = FakeOpenWeather()
    sdk.result_direct = [_location(name="Sao Paulo", state="São Paulo")]
    adapter = OpenWeatherProviderAdapter(sdk_client=sdk)

    result = await adapter.resolve_city(CityQuery(city="Sao Paulo", state="sao paulo", country="BR", zipcode=None))

    assert result.state == "São Paulo"

@pytest.mark.asyncio
async def test_resolve_city_name_normalization_ignores_accent_and_case() -> None:
    sdk = FakeOpenWeather()
    sdk.result_direct = [_location(name="São Paulo", state="Sao Paulo")]
    adapter = OpenWeatherProviderAdapter(sdk_client=sdk)

    result = await adapter.resolve_city(CityQuery(city="sao paulo", state="Sao Paulo", country="BR", zipcode=None))

    assert result.name == "São Paulo"
