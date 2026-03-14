# Desafio Caiena - Publicador de Comentários de Clima em Gist

API HTTP em Python (FastAPI) que integra com:
- OpenWeatherMap (clima atual + previsão de 5 dias)
- GitHub Gist (publicação de comentário)

A aplicação recebe a cidade e o `gist_id`, gera uma frase em português com temperatura atual e média diária dos próximos dias, e publica esse texto como comentário no Gist.

## Requisitos

- Python 3.12+
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

4. Instale/sincronize dependências:

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

## Executar com Docker

1. Garanta que o arquivo `.env` esteja preenchido.
2. Suba a API com Docker Compose:

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
  "city": "São Paulo",
  "state": "São Paulo",
  "country": "BR",
  "zipcode": "01001-000"
}
```

Campos:
- `gist_id` (obrigatório)
- `city` (obrigatório)
- `state` (opcional, aceita nome completo como `São Paulo`)
- `country` (opcional, código ISO-3166 alfa-2, ex: `BR`)
- `zipcode` (opcional, busca prioritária por CEP + país se informado)

#### Exemplo com curl

```bash
curl -X POST 'http://localhost:8000/v1/gists/weather-comments' \
  -H 'Content-Type: application/json' \
  -d '{
    "gist_id": "SEU_GIST_ID",
    "city": "São Paulo",
    "state": "São Paulo",
    "country": "BR",
    "zipcode": "01001-000"
  }'
```

#### Exemplo de resposta (200)

```json
{
  "gist_id": "SEU_GIST_ID",
  "comment_id": 123456789,
  "comment": "34°C e nublado em São Paulo, São Paulo em 12/12. Média para os próximos dias: 32°C em 13/12, 25°C em 14/12, 29°C em 15/12, 33°C em 16/12 e 28°C em 17/12."
}
```

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
- `src/integrations/openweather/`: SDK OpenWeatherMap
- `src/integrations/github_gist/`: integração com GitHub Gist (PyGithub)
- `src/api/`: API FastAPI
- `src/shared/`: configuração e exceções compartilhadas
- `tests/unit/weather_comment_publishing/`: testes unitários de domínio (formatter, service e types)
- `tests/unit/integrations/`: testes unitários das integrações
