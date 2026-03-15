
import os

from fastapi.routing import APIRouter

from src.shared.settings import Settings
from src.weather_comment_publishing.types import CityQuery
from src.api.schemas import (
    CityLocationRequest,
    ErrorResponse,
    PublishWeatherCommentRequest,
    PublishWeatherCommentResponse,
)
from src.weather_comment_publishing.formatter import WeatherCommentFormatter
from src.weather_comment_publishing.service import WeatherCommentService
from src.integrations.github_gist.client import GitHubGistClient
from src.integrations.openweather.client import OpenWeatherApiClient


git_gist_router = APIRouter(prefix="/v1/gists", tags=["github_gist"])


def _build_weather_comment_service(settings: Settings) -> WeatherCommentService:
    openweather_client = OpenWeatherApiClient(
        api_key=settings.openweather_api_key,
        base_url=settings.openweather_base_url,
        language=settings.openweather_language,
        units=settings.openweather_units,
        timeout_seconds=settings.http_timeout_seconds,
    )
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
    summary="Publica comentário de clima em um Gist",
    description=(
        "Recebe um alvo de localidade por cidade ou CEP, consulta clima atual e previsão diária, "
        "gera o comentário em português e publica no Gist informado."
    ),
    response_description="Comentário publicado com sucesso no Gist.",
    response_model=PublishWeatherCommentResponse,
    responses={
        400: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
    },
    openapi_extra={
        "requestBody": {
            "content": {
                "application/json": {
                    "examples": {
                        "by_city": {
                            "summary": "Busca por cidade",
                            "value": {
                                "gist_id": "SEU_GIST_ID",
                                "location": {
                                    "kind": "city",
                                    "city": "Sao Paulo",
                                    "state": "Sao Paulo",
                                    "country": "BR",
                                },
                            },
                        },
                        "by_zipcode": {
                            "summary": "Busca por CEP",
                            "value": {
                                "gist_id": "SEU_GIST_ID",
                                "location": {
                                    "kind": "zipcode",
                                    "zipcode": "01001000",
                                    "country": "BR",
                                },
                            },
                        },
                    },
                },
            },
        },
    },
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
