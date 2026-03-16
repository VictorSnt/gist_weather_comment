# RFC 001 — weather_comment_publishing

**Status:** Draft  
**Autor:** Victor Santos  
**Data:** 2026-03-14  
**Versão:** 0.0.3

---

## 1. Objetivo

Definir o módulo `weather_comment_publishing`, responsável por publicar comentários meteorológicos em Gists.

O módulo recebe uma consulta de localidade e um identificador de Gist, resolve coordenadas da localidade, obtém clima atual e previsão de 5 dias, gera um comentário textual em português e publica no Gist.

---

## 2. Responsabilidades

- Receber os dados de entrada do caso de uso
- Resolver localidade para coordenadas geográficas
- Consultar clima atual
- Consultar previsão de 5 dias
- Gerar texto final do comentário
- Publicar comentário no Gist
- Retornar resultado da publicação

---

## 3. Tipos de Dados

### 3.1. Coordinates

| Campo       | Tipo  | Restrição |
|-------------|-------|-----------|
| `latitude`  | float | -90 a 90  |
| `longitude` | float | -180 a 180|

Imutável, sem campos extras.

### 3.2. CityQuery

| Campo     | Tipo        | Obrigatório | Observação |
|-----------|-------------|-------------|------------|
| `city`    | str ou None | Não         | Não pode ser vazio quando informado |
| `state`   | str ou None | Não         | Deve ser nome completo (sem sigla), espaços normalizados |
| `country` | str ou None | Não         | ISO-3166 alfa-2, normalizado para maiúsculas |
| `zipcode` | str ou None | Não         | Não pode ser vazio quando informado |

Imutável, sem campos extras.

Regras combinadas de `CityQuery`:

- Deve informar exatamente um entre `city` e `zipcode`
- `state` só pode ser informado quando `city` for informado
- `zipcode` exige `country`
- Para `country=BR`, `zipcode` deve conter 8 dígitos e é normalizado para `12345-678`

### 3.3. ResolvedLocation

| Campo         | Tipo        | Obrigatório |
|---------------|-------------|-------------|
| `name`        | str         | Sim         |
| `state`       | str ou None | Não         |
| `country`     | str         | Sim         |
| `coordinates` | Coordinates | Sim         |

Imutável, sem campos extras.

### 3.4. WeatherCondition

| Campo         | Tipo | Obrigatório |
|---------------|------|-------------|
| `code`        | int  | Sim         |
| `group`       | str  | Sim         |
| `description` | str  | Sim         |
| `icon`        | str  | Sim         |

Imutável, sem campos extras.

### 3.5. CurrentWeather

| Campo                 | Tipo             | Obrigatório | Observação |
|-----------------------|------------------|-------------|------------|
| `temperature_celsius` | float            | Sim         |            |
| `condition`           | WeatherCondition | Sim         | Condição principal atual |
| `observed_at`         | datetime         | Sim         | Com timezone |

Imutável, sem campos extras.

### 3.6. ForecastEntry

| Campo                 | Tipo     | Obrigatório | Observação |
|-----------------------|----------|-------------|------------|
| `forecasted_at`       | datetime | Sim         | Com timezone |
| `temperature_celsius` | float    | Sim         |            |

Imutável, sem campos extras.

### 3.7. PublishedWeatherComment

| Campo        | Tipo             | Obrigatório |
|--------------|------------------|-------------|
| `gist_id`    | str              | Sim         |
| `comment_id` | int              | Sim         |
| `location`   | ResolvedLocation | Sim         |
| `comment`    | str              | Sim         |

Imutável, sem campos extras.

---

## 4. Contratos

### 4.1. Caso de Uso

```python
async def publish_weather_comment(
    *,
    gist_id: str,
    city_query: CityQuery,
) -> PublishedWeatherComment
```

### 4.2. Provider de Clima

```python
async def resolve_city(query: CityQuery) -> ResolvedLocation
async def get_current_weather(coordinates: Coordinates) -> CurrentWeather
async def get_five_day_forecast(coordinates: Coordinates) -> list[ForecastEntry]
```

### 4.3. Publisher de Gist

```python
async def publish_comment(gist_id: str, content: str) -> int
```

### 4.4. Formatter

```python
def format_comment(
    location: ResolvedLocation,
    current_weather: CurrentWeather,
    forecast_entries: Sequence[ForecastEntry],
) -> str
```

---

## 5. Regras de Formatação

O comentário gerado deve:

- Usar temperatura atual arredondada
- Usar descrição da condição principal atual
- Exibir apenas o nome da cidade (sem estado)
- Exibir data observada no formato `dd/mm`
- Agrupar previsão por dia e calcular média diária de temperatura
- Considerar apenas dias posteriores ao dia observado
- Limitar quantidade de dias conforme configuração

Formato:

`34°C e nublado em <cidade> em 12/12. Média para os próximos dias: 32°C em 13/12, 25°C em 14/12, 29°C em 15/12, 33°C em 16/12 e 28°C em 17/12.`

A segunda frase só aparece quando houver previsão futura.

---

## 6. Fluxo de Execução

1. Receber `gist_id` e `city_query` (já validado com estratégia única: cidade ou CEP)
2. Resolver localidade via `resolve_city` conforme estratégia:
   - `zipcode` + `country`: busca por CEP
   - `city` (+ filtros opcionais): busca por nome
3. Buscar clima atual via `get_current_weather`
4. Buscar previsão via `get_five_day_forecast`
5. Gerar texto com `format_comment`
6. Publicar no Gist via `publish_comment`
7. Retornar `PublishedWeatherComment`

---

## 7. Estrutura do Módulo

```text
weather_comment_publishing/
├── adapters/
│   └── openweather_provider.py
├── types.py
├── protocols.py
├── formatter.py
└── service.py
```
