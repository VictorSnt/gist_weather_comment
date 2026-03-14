# RFC 001 — weather_comment_publishing

**Status:** Draft  
**Autor:** Victor Santos  
**Data:** 2026-03-14

---

## 1. Objetivo

Definir o módulo `weather_comment_publishing`, responsável por publicar comentários meteorológicos em Gists.

O módulo recebe uma consulta de localidade e um identificador de Gist, resolve as coordenadas da localidade, obtém o clima atual e a previsão, gera um comentário textual descritivo e o publica no Gist especificado.

---

## 2. Responsabilidades

O módulo implementa o caso de uso de publicação de comentário meteorológico, orquestrando as seguintes etapas:

- Receber os dados de entrada
- Resolver a localidade consultada para coordenadas geográficas
- Consultar dados meteorológicos atuais e previsão
- Transformar os dados em texto descritivo
- Publicar o comentário no Gist
- Retornar o resultado da operação

---

## 3. Tipos de Dados

### 3.1. Coordinates

Representa coordenadas geográficas.

| Campo       | Tipo  | Restrição          |
|-------------|-------|---------------------|
| `latitude`  | float | -90 a 90            |
| `longitude` | float | -180 a 180          |

Imutável, sem campos extras.

### 3.2. CityQuery

Consulta de localidade fornecida pelo chamador.

| Campo     | Tipo        | Obrigatório | Observação                             |
|-----------|-------------|-------------|----------------------------------------|
| `city`    | str         | Sim         | Não pode ser vazio                     |
| `state`   | str ou None | Não         | Nome completo, sem sigla               |
| `country` | str ou None | Não         | Código ISO 2 letras, normalizado para maiúsculas |

Imutável, sem campos extras.

### 3.3. ResolvedLocation

Localidade resolvida com coordenadas.

| Campo         | Tipo        | Obrigatório | Observação                    |
|---------------|-------------|-------------|-------------------------------|
| `name`        | str         | Sim         | Não vazio                     |
| `state`       | str ou None | Não         |                               |
| `country`     | str         | Sim         | ISO 2 letras, maiúsculo       |
| `coordinates` | Coordinates | Sim         | Válidas conforme regras       |

Imutável, sem campos extras.

### 3.4. WeatherCondition

Condição meteorológica.

| Campo         | Tipo  | Obrigatório |
|---------------|-------|-------------|
| `code`        | int   | Sim         |
| `group`       | str   | Sim         |
| `description` | str   | Sim         |
| `icon`        | str   | Sim         |

Imutável, sem campos extras.

### 3.5. CurrentWeather

Clima atual.

| Campo                | Tipo                     | Obrigatório | Observação                           |
|----------------------|--------------------------|-------------|--------------------------------------|
| `temperature_celsius`| float                    | Sim         |                                      |
| `conditions`         | list[WeatherCondition]   | Sim         | Pelo menos um item                   |
| `observed_at`        | datetime                 | Sim         | Com timezone, descrição principal no primeiro item |

Imutável, sem campos extras.

### 3.6. ForecastEntry

Entrada de previsão.

| Campo                | Tipo                     | Obrigatório | Observação                           |
|----------------------|--------------------------|-------------|--------------------------------------|
| `forecasted_at`      | datetime                 | Sim         | Com timezone                         |
| `temperature_celsius`| float                    | Sim         |                                      |
| `conditions`         | list[WeatherCondition]   | Sim         | Pelo menos um item, descrição principal no primeiro |

Imutável, sem campos extras.

### 3.7. PublishedWeatherComment

Resultado da publicação.

| Campo        | Tipo             | Obrigatório | Observação               |
|--------------|------------------|-------------|--------------------------|
| `gist_id`    | str              | Sim         | Não vazio                |
| `comment_id` | int              | Sim         | Maior que zero           |
| `location`   | ResolvedLocation | Sim         | Localidade utilizada     |
| `comment`    | str              | Sim         | Texto publicado, não vazio |

Imutável, sem campos extras.

---

## 4. Contratos

### 4.1. Interface Pública

```python
def publish_weather_comment(
    *,
    gist_id: str,
    city_query: CityQuery
) -> PublishedWeatherComment
```

**Entrada:**
- `gist_id`: identificador do Gist de destino
- `city_query`: consulta estruturada da localidade

**Saída:** objeto `PublishedWeatherComment` com os dados da publicação.

### 4.2. Provider de Clima

Dependência com operações assíncronas:

```python
async def resolve_city(query: CityQuery) -> ResolvedLocation
async def get_current_weather(coordinates: Coordinates) -> CurrentWeather
async def get_five_day_forecast(coordinates: Coordinates) -> list[ForecastEntry]
```

### 4.3. Publisher de Gist

Dependência com operação assíncrona:

```python
async def publish_comment(gist_id: str, content: str) -> int
```

Retorna o identificador do comentário criado.

### 4.4. Formatter

Dependência síncrona:

```python
def format_comment(
    location: ResolvedLocation,
    current_weather: CurrentWeather,
    forecast_entries: Sequence[ForecastEntry]
) -> str
```

Gera o texto do comentário em português.

---

## 5. Regras de Formatação

O comentário gerado deve:

- Utilizar temperatura atual arredondada
- Incluir descrição principal do clima atual
- Exibir nome da cidade e estado (quando disponível)
- Apresentar data observada no formato `dd/mm`
- Agrupar previsões por dia, calculando temperatura média
- Considerar apenas dias posteriores ao observado
- Limitar quantidade de dias conforme configuração
- Ser escrito em português

**Estrutura esperada:**

> "Hoje em [cidade/estado] faz [temperatura]°C e [descrição].  
> Nos próximos dias, a média fica em [temperatura média]°C."

Incluir apenas a segunda frase quando houver previsão disponível.

---

## 6. Fluxo de Execução

1. Receber `gist_id` e `city_query`
2. Resolver localidade via `resolve_city`
3. Obter clima atual via `get_current_weather` com as coordenadas
4. Obter previsão via `get_five_day_forecast` com as mesmas coordenadas
5. Gerar texto do comentário via `format_comment`
6. Publicar no Gist via `publish_comment`
7. Retornar `PublishedWeatherComment`

---

## 7. Estrutura do Módulo

```
weather_comment_publishing/
├── types.py          # Modelos de domínio
├── protocols.py      # Contratos das dependências
├── formatter.py      # Geração do comentário
└── service.py        # Orquestração do caso de uso
```