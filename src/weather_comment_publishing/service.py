from __future__ import annotations

from dataclasses import dataclass

from src.weather_comment_publishing.protocols import GistPublisherPort, WeatherCommentFormatterPort, WeatherProviderPort
from src.weather_comment_publishing.types import CityQuery, PublishedWeatherComment


@dataclass(frozen=True, slots=True)
class WeatherCommentService:
    openweather_client: WeatherProviderPort
    github_gist_client: GistPublisherPort
    formatter: WeatherCommentFormatterPort

    async def publish_weather_comment(self, *, gist_id: str, city_query: CityQuery) -> PublishedWeatherComment:
        resolved_location = await self.openweather_client.resolve_city(query=city_query)
        current_weather = await self.openweather_client.get_current_weather(coordinates=resolved_location.coordinates)
        forecast_entries = await self.openweather_client.get_five_day_forecast(coordinates=resolved_location.coordinates)
        comment = self.formatter.format_comment(
            location=resolved_location,
            current_weather=current_weather,
            forecast_entries=forecast_entries,
        )
        comment_id = await self.github_gist_client.publish_comment(gist_id=gist_id, content=comment)
        return PublishedWeatherComment(
            gist_id=gist_id,
            comment_id=comment_id,
            location=resolved_location,
            comment=comment,
        )
