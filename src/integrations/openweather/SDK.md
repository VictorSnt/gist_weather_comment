# OpenWeather SDK

## Objetivo

Este módulo encapsula a integração HTTP com OpenWeather com contrato próprio de:

- tipos de entrada/saída
- exceções
- comportamento de erro

Ele pode ser usado diretamente por qualquer aplicação Python sem depender do domínio de `weather_comment_publishing`.

## API pública

Import recomendado:

```python
from src.integrations.openweather import (
    OpenWeather,
    Coordinates,
    OpenWeatherNotFoundError,
    OpenWeatherRequestError,
    OpenWeatherContractError,
)
```

### Cliente

```python
OpenWeather(
    api_key: str,
    base_url: str,
    language: str,
    units: str,
    timeout_seconds: float,
)
```

### Métodos

- `geocode_zip(zipcode: str, country_code: str) -> ResolvedLocation`
- `geocode_direct(city: str, state: str | None = None, country_code: str | None = None, limit: int = 5) -> list[ResolvedLocation]`
- `read_current_weather(coordinates: Coordinates) -> CurrentWeather`
- `read_five_day_forecast(coordinates: Coordinates) -> list[ForecastEntry]`

## Modelos

### `LocationQuery`

- estratégia exclusiva: cidade **ou** CEP
- regras:
  - `city` e `zipcode` não podem coexistir
  - `zipcode` exige `country`
  - `state` exige `city`
- para `country=BR`, `zipcode` é normalizado para `12345-678`

### `ResolvedLocation`

- `name`, `state`, `country`, `coordinates`

### `CurrentWeather`

- `temperature_celsius`, `condition`, `observed_at`

### `ForecastEntry`

- `forecasted_at`, `temperature_celsius`

## Estratégia de erros

- `OpenWeatherNotFoundError`:
  - localização não encontrada (ex.: CEP/cidade inexistente)
- `OpenWeatherRequestError`:
  - falhas HTTP/transporte/upstream (timeout, 4xx/5xx não semânticos)
- `OpenWeatherContractError`:
  - quebra de contrato esperado do provider (ex.: 404 inesperado em endpoint conhecido)

## Exemplo de uso

```python
import asyncio

from src.integrations.openweather import (
    OpenWeather,
    OpenWeatherNotFoundError,
)


async def main() -> None:
    client = OpenWeather(
        api_key="your-api-key",
        base_url="https://api.openweathermap.org",
        language="pt_br",
        units="metric",
        timeout_seconds=10.0,
    )

    try:
        location = await client.geocode_zip(zipcode="01001000", country_code="BR")
    except OpenWeatherNotFoundError:
        print("Localização não encontrada")
        return

    current = await client.read_current_weather(location.coordinates)
    forecast = await client.read_five_day_forecast(location.coordinates)
    print(location.name, current.temperature_celsius, len(forecast))


if __name__ == "__main__":
    asyncio.run(main())
```

## Uso na aplicação atual

O domínio da aplicação usa o adaptador:

- `src/weather_comment_publishing/adapters/openweather_provider.py`

Esse adaptador traduz erros/tipos da SDK para o contrato `WeatherProviderPort` da aplicação.
