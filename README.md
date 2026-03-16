# Desafio Caiena - Publicador de Comentários de Clima em Gist

API HTTP em Python (FastAPI) que integra com:
- OpenWeatherMap (clima atual + previsão de 5 dias)
- GitHub Gist (publicação de comentário)

A aplicação recebe um alvo de localidade (cidade ou CEP) e o `gist_id`, gera uma frase em português com temperatura atual e média diária dos próximos dias, e publica esse texto como comentário no Gist.

## Requisitos

- Python 3.12.x
- [uv](https://docs.astral.sh/uv/)
- Chave da API OpenWeatherMap
- Token clássico do GitHub com permissão para Gist (`gist` scope)

## Configuração

1. Copie o arquivo de exemplo de variáveis de ambiente:

```bash
cp .env.example .env
```

2. Preencha as variáveis obrigatórias no `.env`:

- `OPENWEATHER_API_KEY`
- `GITHUB_TOKEN`

3. Exporte as variáveis para o shell atual (uma forma simples):

```bash
set -a
source .env
set +a
```

4. Instale/sincronize dependências (usa o `uv.lock` versionado para garantir reprodutibilidade):

```bash
make sync
```

## Comandos (Makefile)

- Subir API:

```bash
make run
```

- Rodar testes:

```bash
make test
```

- Rodar testes com saída detalhada:

```bash
make test-verbose
```

- Ver ajuda:

```bash
make help
```

## Executar com Docker (produção-like)

- Requisitos: Docker e Docker Compose.
- O build já instala as dependências de produção a partir do `uv.lock` (sem dev), sem depender de cache local.

1. Garanta que o arquivo `.env` esteja preenchido (será lido pelo Compose).
2. Faça o build e suba a API:

```bash
docker compose up --build
```

3. A API ficará disponível em `http://localhost:${HTTP_SERVER_PORT}` (ou `8000` por padrão).

## Endpoint

### `POST /v1/gists/weather-comments`

Publica um comentário de clima no Gist informado.

#### Body JSON

```json
{
  "gist_id": "<id-do-gist>",
  "location": {
    "kind": "city",
    "city": "Sao Paulo",
    "state": "Sao Paulo",
    "country": "BR"
  }
}
```

Campos:
- `gist_id` (obrigatório)
- `location.kind` (obrigatório): `city` ou `zipcode`
- `location.city` (obrigatório quando `kind=city`)
- `location.state` (opcional quando `kind=city`, nome completo)
- `location.country` (opcional em `city`, obrigatório em `zipcode`, ISO-3166 alfa-2)
- `location.zipcode` (obrigatório quando `kind=zipcode`)
- Para `country=BR`, o CEP aceita `01001000` ou `01001-000` e será normalizado para `01001-000`

#### Exemplo com curl

```bash
curl -X POST 'http://localhost:8000/v1/gists/weather-comments' \
  -H 'Content-Type: application/json' \
  -d '{
    "gist_id": "SEU_GIST_ID",
    "location": {
      "kind": "zipcode",
      "zipcode": "01001000",
      "country": "BR"
    }
  }'
```

#### Exemplo de resposta (200)

```json
{
  "gist_id": "SEU_GIST_ID",
  "comment_id": 123456789,
  "comment": "34°C e nublado em Sao Paulo em 12/12. Média para os próximos dias: 32°C em 13/12, 25°C em 14/12, 29°C em 15/12, 33°C em 16/12 e 28°C em 17/12."
}
```

#### Erros (formato padrão)

Todos os erros seguem o formato:

```json
{
  "error_code": "string",
  "message": "string",
  "field": "string|null"
}
```

Principais códigos:
- `422 invalid_request`: payload inválido / schema incorreto.
- `404 location_not_found` ou `gist_not_found`.
- `403 gist_access_denied` ou `gist_comment_not_allowed`.
- `409 location_ambiguous`.
- `500 integration_contract_error` (contrato OpenWeather quebrado), `configuration_error`, `internal_error`.
- `502 upstream_failure` (falha de transporte/disponibilidade do provider).

## Saúde da aplicação

- `GET /health`

Resposta esperada:

```json
{
  "status": "ok"
}
```

## Estrutura resumida

- `src/weather_comment_publishing/`: núcleo de domínio/aplicação (formatter, service, types, protocols)
- `src/integrations/openweather/`: SDK OpenWeatherMap (documentação em `src/integrations/openweather/SDK.md`)
- `src/integrations/github_gist/`: integração com GitHub Gist (PyGithub)
- `src/api/`: API FastAPI
- `src/shared/`: configuração e exceções compartilhadas
- `tests/weather_comment_publishing/unit/`: testes unitários de domínio
- `tests/api/integration/`: testes de integração da API
