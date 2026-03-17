from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from src.weather_comment_publishing.formatter import WeatherCommentFormatter
from src.weather_comment_publishing.types import (
    Coordinates,
    CurrentWeather,
    ForecastEntry,
    ResolvedLocation,
    WeatherCondition,
)


class TestWeatherCommentFormatter:
    """Testes para o WeatherCommentFormatter."""

    def test_format_comment_limits_forecast_to_five_future_days(
        self,
        resolved_location: ResolvedLocation,
        current_weather: CurrentWeather,
    ) -> None:
        """Deve limitar a previsão a 5 dias futuros."""
        formatter = WeatherCommentFormatter(forecast_days_limit=5)
        
        # Cria entradas para 6 dias futuros
        entries = [
            ForecastEntry(
                forecasted_at=current_weather.observed_at + timedelta(days=day, hours=9),
                temperature_celsius=20.0 + day,
            )
            for day in range(1, 7)
        ]

        comment = formatter.format_comment(
            location=resolved_location,
            current_weather=current_weather,
            forecast_entries=entries,
        )

        self._assert_first_sentence(
            comment,
            temperature=int(round(current_weather.temperature_celsius)),
            condition=current_weather.condition.description,
            city=resolved_location.name,
            date=current_weather.observed_at.strftime("%d/%m"),
        )
        
        assert "Média para os próximos dias:" in comment
        assert "21°C em" in comment  # dia 2
        assert "25°C em" in comment  # dia 6
        assert "26°C em" not in comment  # dia 7 não deve aparecer

    def test_format_comment_uses_conjunction_for_two_forecast_days(
        self,
        resolved_location: ResolvedLocation,
        current_weather: CurrentWeather,
    ) -> None:
        """Deve usar 'e' para conjunção de dois dias."""
        formatter = WeatherCommentFormatter(forecast_days_limit=5)
        
        base_date = current_weather.observed_at.replace(hour=12)
        entries = [
            ForecastEntry(
                forecasted_at=base_date + timedelta(days=1),
                temperature_celsius=22.0,
            ),
            ForecastEntry(
                forecasted_at=base_date + timedelta(days=2),
                temperature_celsius=24.0,
            ),
        ]

        comment = formatter.format_comment(
            location=resolved_location,
            current_weather=current_weather,
            forecast_entries=entries,
        )

        assert comment.endswith("22°C em 12/03 e 24°C em 13/03.")

    def test_format_comment_with_state_uses_city_only(
        self,
        coordinates: Coordinates,
        current_weather: CurrentWeather,
    ) -> None:
        """Quando state é None, deve usar apenas o nome da cidade."""
        formatter = WeatherCommentFormatter(forecast_days_limit=5)
        
        location = ResolvedLocation(
            name="Rio de Janeiro",
            state="Rio de Janeiro",
            country="BR",
            coordinates=coordinates,
        )
        
        entries = [
            ForecastEntry(
                forecasted_at=current_weather.observed_at + timedelta(days=1),
                temperature_celsius=25.0,
            )
        ]

        comment = formatter.format_comment(
            location=location,
            current_weather=current_weather,
            forecast_entries=entries,
        )

        assert f"em Rio de Janeiro em" in comment

    def test_format_comment_ignores_same_day_average_in_forecast_sentence(
        self,
        resolved_location: ResolvedLocation,
        current_weather: CurrentWeather,
    ) -> None:
        """Não deve incluir médias do dia atual na frase de previsão."""
        formatter = WeatherCommentFormatter(forecast_days_limit=5)
        
        base_date = current_weather.observed_at.replace(hour=0)
        
        # Mesmo dia (deve ignorar)
        same_day_entries = [
            ForecastEntry(
                forecasted_at=base_date + timedelta(hours=9),
                temperature_celsius=10.0,
            ),
            ForecastEntry(
                forecasted_at=base_date + timedelta(hours=15),
                temperature_celsius=40.0,
            ),
        ]
        
        # Dia seguinte (deve incluir)
        next_day_entries = [
            ForecastEntry(
                forecasted_at=base_date + timedelta(days=1, hours=9),
                temperature_celsius=26.0,
            ),
            ForecastEntry(
                forecasted_at=base_date + timedelta(days=1, hours=18),
                temperature_celsius=28.0,
            ),
        ]
        
        entries = same_day_entries + next_day_entries

        comment = formatter.format_comment(
            location=resolved_location,
            current_weather=current_weather,
            forecast_entries=entries,
        )

        assert "Média para os próximos dias: 27°C em 12/03." in comment

    def test_format_comment_orders_forecast_dates_even_if_entries_are_unsorted(
        self,
        resolved_location: ResolvedLocation,
        current_weather: CurrentWeather,
    ) -> None:
        """Deve ordenar as previsões por data, mesmo se entrada estiver fora de ordem."""
        formatter = WeatherCommentFormatter(forecast_days_limit=5)
        
        base_date = current_weather.observed_at.replace(hour=12)
        entries = [
            ForecastEntry(
                forecasted_at=base_date + timedelta(days=2),
                temperature_celsius=30.0,
            ),
            ForecastEntry(
                forecasted_at=base_date + timedelta(days=1),
                temperature_celsius=20.0,
            ),
        ]

        comment = formatter.format_comment(
            location=resolved_location,
            current_weather=current_weather,
            forecast_entries=entries,
        )

        assert "20°C em 12/03 e 30°C em 13/03." in comment

    def test_format_comment_returns_only_first_sentence_when_forecast_is_empty(
        self,
        resolved_location: ResolvedLocation,
        current_weather: CurrentWeather,
    ) -> None:
        """Sem previsão, deve retornar apenas a primeira frase."""
        formatter = WeatherCommentFormatter(forecast_days_limit=5)

        comment = formatter.format_comment(
            location=resolved_location,
            current_weather=current_weather,
            forecast_entries=[],
        )

        expected = (
            f"{int(round(current_weather.temperature_celsius))}°C e "
            f"{current_weather.condition.description} em {resolved_location.name} "
            f"em {current_weather.observed_at.strftime('%d/%m')}."
        )
        assert comment == expected

    def test_format_comment_uses_commas_and_conjunction_for_three_or_more_days(
        self,
        resolved_location: ResolvedLocation,
        current_weather: CurrentWeather,
    ) -> None:
        """Para 3+ dias, usa vírgulas e 'e' no último."""
        formatter = WeatherCommentFormatter(forecast_days_limit=5)
        
        base_date = current_weather.observed_at.replace(hour=12)
        entries = [
            ForecastEntry(
                forecasted_at=base_date + timedelta(days=i),
                temperature_celsius=20.0 + i,
            )
            for i in range(1, 4)
        ]

        comment = formatter.format_comment(
            location=resolved_location,
            current_weather=current_weather,
            forecast_entries=entries,
        )

        assert ", 22°C em 13/03 e 23°C em 14/03." in comment

    def test_format_comment_respects_custom_forecast_limit(
        self,
        resolved_location: ResolvedLocation,
        current_weather: CurrentWeather,
    ) -> None:
        """Deve respeitar o limite customizado de dias de previsão."""
        formatter = WeatherCommentFormatter(forecast_days_limit=2)
        
        base_date = current_weather.observed_at.replace(hour=12)
        entries = [
            ForecastEntry(
                forecasted_at=base_date + timedelta(days=i),
                temperature_celsius=20.0 + i,
            )
            for i in range(1, 4)
        ]

        comment = formatter.format_comment(
            location=resolved_location,
            current_weather=current_weather,
            forecast_entries=entries,
        )

        assert "21°C em 12/03 e 22°C em 13/03." in comment
        assert "23°C" not in comment

    def test_format_comment_matches_challenge_sentence_shape(
        self,
    ) -> None:
        """Teste de aceitação: deve gerar exatamente o formato esperado."""
        formatter = WeatherCommentFormatter(forecast_days_limit=5)
        
        weather_condition = WeatherCondition(
            code=803,
            group="Clouds",
            description="nublado",
            icon="04d"
        )
        
        location = ResolvedLocation(
            name="Sao Paulo",
            state="Sao Paulo",
            country="BR",
            coordinates=Coordinates(latitude=-23.55, longitude=-46.63),
        )
        
        current_weather = CurrentWeather(
            temperature_celsius=34.0,
            condition=weather_condition,
            observed_at=datetime(2026, 12, 12, 12, 0, tzinfo=UTC),
        )
        
        forecast_entries = [
            ForecastEntry(
                forecasted_at=datetime(2026, 12, day, 9, 0, tzinfo=UTC),
                temperature_celsius=temp,
            )
            for day, temp in [(13, 32.0), (14, 25.0), (15, 29.0), (16, 33.0), (17, 28.0)]
        ]

        comment = formatter.format_comment(
            location=location,
            current_weather=current_weather,
            forecast_entries=forecast_entries,
        )

        expected = (
            "34°C e nublado em Sao Paulo em 12/12. Média para os próximos dias: "
            "32°C em 13/12, 25°C em 14/12, 29°C em 15/12, 33°C em 16/12 e 28°C em 17/12."
        )
        assert comment == expected

    # Método auxiliar privado
    def _assert_first_sentence(
        self,
        comment: str,
        *,
        temperature: int,
        condition: str,
        city: str,
        date: str,
    ) -> None:
        """Verifica a primeira frase do comentário."""
        assert comment.startswith(f"{temperature}°C e {condition} em {city} em {date}.")