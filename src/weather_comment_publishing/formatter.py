from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from statistics import fmean
from typing import Sequence

from src.weather_comment_publishing.types import CurrentWeather, ForecastEntry, ResolvedLocation


@dataclass(frozen=True, slots=True)
class WeatherCommentFormatter:
    forecast_days_limit: int

    def format_comment(
        self,
        *,
        location: ResolvedLocation,
        current_weather: CurrentWeather,
        forecast_entries: Sequence[ForecastEntry],
    ) -> str:
        observed_date = current_weather.observed_at.date()
        daily_averages = self._daily_average_by_date(forecast_entries)
        next_days = [
            (entry_date, avg_temp) for entry_date, avg_temp in daily_averages if entry_date > observed_date
        ][: self.forecast_days_limit]

        first_sentence = (
            f"{int(round(current_weather.temperature_celsius))}°C e {current_weather.condition.description} "
            f"em {location.name} em {self._format_date(observed_date)}."
        )
        if not next_days:
            return first_sentence

        forecast_parts = [
            f"{int(round(avg_temp))}°C em {self._format_date(forecast_date)}" for forecast_date, avg_temp in next_days
        ]
        second_sentence = f"Média para os próximos dias: {self._join_pt(forecast_parts)}."
        return f"{first_sentence} {second_sentence}"

    def _daily_average_by_date(self, entries: Sequence[ForecastEntry]) -> list[tuple[date, float]]:
        grouped_temperatures: dict[date, list[float]] = defaultdict(list)
        for entry in entries:
            grouped_temperatures[entry.forecasted_at.date()].append(entry.temperature_celsius)
        averages = [(forecast_date, fmean(temperatures)) for forecast_date, temperatures in grouped_temperatures.items()]
        averages.sort(key=lambda value: value[0]) # sort by date
        return averages

    def _format_date(self, value: date) -> str:
        return f"{value.day:02d}/{value.month:02d}"

    def _join_pt(self, values: list[str]) -> str:
        if len(values) <= 1:
            return "".join(values)
        if len(values) == 2:
            return f"{values[0]} e {values[1]}"
        return f"{', '.join(values[:-1])} e {values[-1]}"
