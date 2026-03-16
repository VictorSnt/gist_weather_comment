import os
from functools import lru_cache

from fastapi import Depends
from fastapi.routing import APIRouter

from src.api.routes.github_gist.api_doc import publish_weather_comment_doc
from src.api.schemas import (
    CityLocationRequest,
    PublishWeatherCommentRequest,
    PublishWeatherCommentResponse,
)
from src.integrations.github_gist.client import GitHubGistClient
from src.integrations.openweather import OpenWeather
from src.shared.settings import Settings
from src.weather_comment_publishing.adapters.openweather_provider import (
    OpenWeatherProviderAdapter,
)
from src.weather_comment_publishing.formatter import WeatherCommentFormatter
from src.weather_comment_publishing.service import WeatherCommentService
from src.weather_comment_publishing.types import CityQuery


github_gist_router = APIRouter(prefix="/v1/gists", tags=["github_gist"])


@lru_cache
def get_settings() -> Settings:
    return Settings.from_env(os.environ)


def _build_weather_comment_service(settings: Settings) -> WeatherCommentService:
    openweather_sdk = OpenWeather(
        api_key=settings.openweather_api_key,
        base_url=settings.openweather_base_url,
        language=settings.openweather_language,
        units="metric",
        timeout_seconds=settings.http_timeout_seconds,
    )
    openweather_client = OpenWeatherProviderAdapter(sdk_client=openweather_sdk)
    github_client = GitHubGistClient(token=settings.github_token)
    formatter = WeatherCommentFormatter(
        forecast_days_limit=settings.forecast_days_limit
    )

    return WeatherCommentService(
        openweather_client=openweather_client,
        github_gist_client=github_client,
        formatter=formatter,
    )


@lru_cache
def get_weather_comment_service() -> WeatherCommentService:
    settings = get_settings()
    return _build_weather_comment_service(settings=settings)


def _to_city_query(request: PublishWeatherCommentRequest) -> CityQuery:
    location = request.location

    if isinstance(location, CityLocationRequest):
        return CityQuery(
            city=location.city,
            state=location.state,
            country=location.country,
            zipcode=None,
        )

    return CityQuery(
        city=None,
        state=None,
        country=location.country,
        zipcode=location.zipcode,
    )


@github_gist_router.post(
    "/weather-comments",
    **publish_weather_comment_doc,
)
async def publish_weather_comment(
    request: PublishWeatherCommentRequest,
    service: WeatherCommentService = Depends(get_weather_comment_service),
) -> PublishWeatherCommentResponse:
    result = await service.publish_weather_comment(
        gist_id=request.gist_id,
        city_query=_to_city_query(request),
    )

    return PublishWeatherCommentResponse(
        gist_id=result.gist_id,
        comment_id=result.comment_id,
        comment=result.comment,
    )