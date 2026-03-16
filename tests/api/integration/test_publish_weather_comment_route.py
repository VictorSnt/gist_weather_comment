from __future__ import annotations

from dataclasses import dataclass

from fastapi.testclient import TestClient
import pytest

from src.api.app import create_app
from src.api.routes.github_gist import router as github_gist_router
from src.shared.exceptions import (
    GistAccessDeniedError,
    GistCommentNotAllowedError,
    GitHubGistIntegrationError,
    LocationAmbiguousError,
    LocationNotFoundError,
    ProviderContractError,
    WeatherProviderError,
)
from src.weather_comment_publishing.types import (
    CityQuery,
    Coordinates,
    PublishedWeatherComment,
    ResolvedLocation,
)


@dataclass
class FakeWeatherCommentService:
    result: PublishedWeatherComment | None = None
    error: Exception | None = None
    received_gist_id: str | None = None
    received_city_query: CityQuery | None = None

    async def publish_weather_comment(
        self,
        *,
        gist_id: str,
        city_query: CityQuery,
    ) -> PublishedWeatherComment:
        self.received_gist_id = gist_id
        self.received_city_query = city_query

        if self.error is not None:
            raise self.error

        assert self.result is not None
        return self.result


def _build_client(
    monkeypatch: pytest.MonkeyPatch,
    *,
    service: FakeWeatherCommentService,
) -> TestClient:
    monkeypatch.setenv("OPENWEATHER_API_KEY", "test-openweather-key")
    monkeypatch.setenv("GITHUB_TOKEN", "test-github-token")
    monkeypatch.setattr(
        github_gist_router,
        "_build_weather_comment_service",
        lambda settings: service,
    )
    return TestClient(create_app())


def _published_comment() -> PublishedWeatherComment:
    return PublishedWeatherComment(
        gist_id="abc123",
        comment_id=123,
        location=ResolvedLocation(
            name="Sao Paulo",
            state="Sao Paulo",
            country="BR",
            coordinates=Coordinates(latitude=-23.55, longitude=-46.63),
        ),
        comment="34°C e nublado em Sao Paulo em 12/12.",
    )


class TestPublishWeatherCommentRoute:
    def test_post_weather_comments_by_city_returns_200_and_normalizes_city_query(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        service = FakeWeatherCommentService(result=_published_comment())
        client = _build_client(monkeypatch, service=service)

        response = client.post(
            "/v1/gists/weather-comments",
            json={
                "gist_id": "abc123",
                "location": {
                    "kind": "city",
                    "city": "Sao Paulo",
                    "state": "Sao Paulo",
                    "country": "br",
                },
            },
        )

        assert response.status_code == 200
        assert response.json() == {
            "gist_id": "abc123",
            "comment_id": 123,
            "comment": "34°C e nublado em Sao Paulo em 12/12.",
        }
        assert service.received_gist_id == "abc123"
        assert service.received_city_query == CityQuery(
            city="Sao Paulo",
            state="Sao Paulo",
            country="BR",
            zipcode=None,
        )

    def test_post_weather_comments_by_zipcode_returns_200_and_normalizes_zipcode_query(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        service = FakeWeatherCommentService(result=_published_comment())
        client = _build_client(monkeypatch, service=service)

        response = client.post(
            "/v1/gists/weather-comments",
            json={
                "gist_id": "abc123",
                "location": {
                    "kind": "zipcode",
                    "zipcode": "01001000",
                    "country": "br",
                },
            },
        )

        assert response.status_code == 200
        assert response.json() == {
            "gist_id": "abc123",
            "comment_id": 123,
            "comment": "34°C e nublado em Sao Paulo em 12/12.",
        }
        assert service.received_gist_id == "abc123"
        assert service.received_city_query == CityQuery(
            city=None,
            state=None,
            country="BR",
            zipcode="01001-000",
        )

    @pytest.mark.parametrize(
        ("error", "expected_status", "expected_error_code"),
        [
            (LocationNotFoundError("Location not found."), 404, "location_not_found"),
            (LocationAmbiguousError("Location is ambiguous."), 409, "location_ambiguous"),
            (ProviderContractError("Unexpected 404 from provider."), 500, "integration_contract_error"),
            (WeatherProviderError("Upstream timeout."), 502, "upstream_failure"),
            (GistAccessDeniedError("Access denied to gist."), 403, "gist_access_denied"),
            (GistCommentNotAllowedError("Not allowed to comment on gist."), 403, "gist_comment_not_allowed"),
            (GitHubGistIntegrationError("GitHub unavailable."), 502, "upstream_failure"),
        ],
    )
    def test_post_weather_comments_maps_domain_errors_to_http_responses(
        self,
        monkeypatch: pytest.MonkeyPatch,
        error: Exception,
        expected_status: int,
        expected_error_code: str,
    ) -> None:
        service = FakeWeatherCommentService(error=error)
        client = _build_client(monkeypatch, service=service)

        response = client.post(
            "/v1/gists/weather-comments",
            json={
                "gist_id": "abc123",
                "location": {
                    "kind": "city",
                    "city": "Sao Paulo",
                },
            },
        )

        assert response.status_code == expected_status
        assert response.json()["error_code"] == expected_error_code

    def test_post_weather_comments_returns_422_for_invalid_request(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        service = FakeWeatherCommentService(result=_published_comment())
        client = _build_client(monkeypatch, service=service)

        response = client.post(
            "/v1/gists/weather-comments",
            json={
                "gist_id": "abc123",
                "location": {
                    "kind": "district",
                    "city": "Sao Paulo",
                },
            },
        )

        assert response.status_code == 422
        assert service.received_gist_id is None
        assert service.received_city_query is None

    @pytest.mark.parametrize(
        "payload",
        [
            {
                "gist_id": "abc123",
                "location": {
                    "kind": "city",
                },
            },
            {
                "gist_id": "abc123",
                "location": {
                    "kind": "zipcode",
                    "country": "BR",
                },
            },
            {
                "gist_id": "abc123",
            },
        ],
    )
    def test_post_weather_comments_returns_422_for_missing_required_fields(
        self,
        monkeypatch: pytest.MonkeyPatch,
        payload: dict[str, object],
    ) -> None:
        service = FakeWeatherCommentService(result=_published_comment())
        client = _build_client(monkeypatch, service=service)

        response = client.post(
            "/v1/gists/weather-comments",
            json=payload,
        )

        data =  response.json()

        assert response.status_code == 422
        assert data["error_code"] == "invalid_request"
        assert data["field"] is not None
        assert service.received_gist_id is None
        assert service.received_city_query is None
