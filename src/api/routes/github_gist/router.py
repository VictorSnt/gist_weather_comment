
import os

from fastapi.routing import APIRouter

from src.api.routes.github_gist.api_doc import publish_weather_comment_doc
from src.shared.settings import Settings
from src.weather_comment_publishing.types import CityQuery
from src.api.schemas import (
    CityLocationRequest,
    PublishWeatherCommentRequest,
    PublishWeatherCommentResponse,
)
from src.weather_comment_publishing.formatter import WeatherCommentFormatter
from src.weather_comment_publishing.service import WeatherCommentService
from src.weather_comment_publishing.adapters.openweather_provider import OpenWeatherProviderAdapter
from src.integrations.github_gist.client import GitHubGistClient
from src.integrations.openweather import OpenWeather


git_gist_router = APIRouter(prefix="/v1/gists", tags=["github_gist"])


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
    formatter = WeatherCommentFormatter(forecast_days_limit=settings.forecast_days_limit)
    return WeatherCommentService(
        openweather_client=openweather_client,
        github_gist_client=github_client,
        formatter=formatter,
    )

@git_gist_router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}

@git_gist_router.post(
    "/weather-comments",
    **publish_weather_comment_doc,
)
async def publish_weather_comment(request: PublishWeatherCommentRequest) -> PublishWeatherCommentResponse:
    location = request.location
    if isinstance(location, CityLocationRequest):
        city_query = CityQuery(city=location.city, state=location.state, country=location.country, zipcode=None)
    else:
        city_query = CityQuery(city=None, state=None, country=location.country, zipcode=location.zipcode)

    service = _build_weather_comment_service(settings=Settings.from_env(os.environ))
    result = await service.publish_weather_comment(
        gist_id=request.gist_id,
        city_query=city_query,
    )
    return PublishWeatherCommentResponse(
        gist_id=result.gist_id,
        comment_id=result.comment_id,
        comment=result.comment,
    )
