# API para publicação de comentários meteorológicos em Gist

API HTTP em Python com **FastAPI** que integra com:

- **OpenWeatherMap** para resolução de localidade, clima atual e previsão de 5 dias
- **GitHub Gist** para publicação do comentário gerado

A aplicação recebe um `gist_id` e uma localidade por **cidade** ou **CEP**, consulta o clima atual e a previsão, calcula a **média diária** dos próximos dias e publica uma frase em português como comentário no Gist informado.

Exemplo de comentário:

```text
34°C e nublado em Sao Paulo em 12/12. Média para os próximos dias: 32°C em 13/12, 25°C em 14/12, 29°C em 15/12, 33°C em 16/12 e 28°C em 17/12.
```

---

## Objetivo do projeto

Este projeto foi construído para atender ao desafio técnico com os seguintes requisitos:

- disponibilizar uma **API HTTP** sem interface gráfica;
- expor um endpoint que receba um identificador de localidade e um `gist_id`;
- consumir a API do **OpenWeatherMap** por meio de um **SDK próprio**;
- publicar o comentário no **GitHub Gist**;
- manter a solução organizada, testável e com baixo acoplamento.

---

## Arquitetura

A aplicação é dividida em camadas:

- `src/integrations/openweather/`: SDK HTTP do OpenWeatherMap
- `src/integrations/github_gist/`: integração com GitHub Gist via PyGithub
- `src/weather_comment_publishing/`: núcleo do caso de uso e regras de negócio
- `src/api/`: camada HTTP com FastAPI
- `src/shared/`: configuração e exceções compartilhadas

Fluxo resumido:

1. a API recebe `gist_id` e `location`;
2. o caso de uso resolve a localidade em coordenadas;
3. busca o clima atual;
4. busca a previsão de 5 dias;
5. agrupa a previsão por dia e calcula a média diária;
6. monta o comentário em português;
7. publica o comentário no Gist;
8. retorna os dados da publicação.

---

## Requisitos

- Python **3.12.x**
- [uv](https://docs.astral.sh/uv/)
- chave da API OpenWeatherMap
- token clássico do GitHub com escopo **`gist`**
- opcionalmente: Docker e Docker Compose

---

## Variáveis de ambiente

Copie o arquivo de exemplo:

```bash
cp .env.example .env
```

Preencha as variáveis obrigatórias:

| Variável | Obrigatória | Descrição | Default |
|---|---:|---|---|
| `OPENWEATHER_API_KEY` | Sim | Chave da API OpenWeatherMap | — |
| `GITHUB_TOKEN` | Sim | Token clássico do GitHub com escopo `gist` | — |
| `OPENWEATHER_BASE_URL` | Não | URL base do provider | `https://api.openweathermap.org` |
| `OPENWEATHER_LANGUAGE` | Não | Idioma enviado ao OpenWeatherMap | `pt_br` |
| `HTTP_CLIENT_TIMEOUT_SECONDS` | Não | Timeout das chamadas HTTP | `10.0` |
| `HTTP_SERVER_HOST` | Não | Host do servidor HTTP | `0.0.0.0` |
| `HTTP_SERVER_PORT` | Não | Porta do servidor HTTP | `8000` |
| `FORECAST_DAYS_LIMIT` | Não | Quantidade máxima de dias exibidos na frase final | `5` |

Uma forma simples de exportar o `.env` no shell atual:

```bash
set -a
source .env
set +a
```

---

## Instalação e execução local

Sincronize as dependências usando o lockfile versionado:

```bash
make sync
```

Suba a API:

```bash
make run
```

A aplicação ficará disponível em:

```text
http://localhost:8000
```

---

## Comandos úteis

```bash
make help
```

Principais targets:

- `make sync`: instala/sincroniza dependências com `uv`
- `make sync-prod`: instala apenas dependências de produção
- `make run`: sobe a API FastAPI com uvicorn
- `make test`: roda a suíte de testes
- `make test-verbose`: roda testes com saída detalhada

---

## Execução com Docker

Com o arquivo `.env` preenchido, rode:

```bash
docker compose up --build
```

A API ficará disponível em:

```text
http://localhost:${HTTP_SERVER_PORT}
```

Se `HTTP_SERVER_PORT` não estiver definido, a porta padrão será `8000`.

---

## Endpoint principal

### `POST /v1/gists/weather-comments`

Publica um comentário meteorológico no Gist informado.

### Body JSON

#### Exemplo por cidade

```json
{
  "gist_id": "SEU_GIST_ID",
  "location": {
    "kind": "city",
    "city": "Sao Paulo",
    "state": "Sao Paulo",
    "country": "BR"
  }
}
```

#### Exemplo por CEP

```json
{
  "gist_id": "SEU_GIST_ID",
  "location": {
    "kind": "zipcode",
    "zipcode": "01001000",
    "country": "BR"
  }
}
```

### Campos aceitos

- `gist_id`: identificador do Gist que receberá o comentário
- `location.kind`: `city` ou `zipcode`
- `location.city`: obrigatório quando `kind=city`
- `location.state`: opcional quando `kind=city`; deve ser nome completo
- `location.country`: opcional em `city` e obrigatório em `zipcode`; ISO-3166 alfa-2
- `location.zipcode`: obrigatório quando `kind=zipcode`

Regras adicionais:

- para `country=BR`, o CEP aceita `01001000` ou `01001-000`;
- internamente, o CEP brasileiro é normalizado para `01001-000`.
- para buscas por cidade, se o OpenWeather retornar múltiplas localidades e
  a consulta não incluir `city`, `state` e `country`, a API retorna
  `location_ambiguous`;
- quando a consulta por cidade inclui `city`, `state` e `country` e mesmo assim
  existirem múltiplos resultados equivalentes, o primeiro retorno do provider é
  utilizado.

### Exemplo com `curl`

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

### Resposta de sucesso

```json
{
  "gist_id": "SEU_GIST_ID",
  "comment_id": 123456789,
  "comment": "34°C e nublado em Sao Paulo em 12/12. Média para os próximos dias: 32°C em 13/12, 25°C em 14/12, 29°C em 15/12, 33°C em 16/12 e 28°C em 17/12."
}
```

---

## Regra de negócio da previsão

A previsão retornada pelo OpenWeatherMap vem em múltiplos pontos de tempo ao longo dos dias. Para gerar a frase final, a aplicação:

- agrupa as entradas de previsão por **dia**;
- calcula a **média diária** da temperatura;
- considera apenas dias **posteriores** ao dia observado no clima atual;
- respeita o limite configurado em `FORECAST_DAYS_LIMIT`.

Se não houver previsão futura aplicável, a resposta contém apenas a primeira frase com o clima atual.

---

## Tratamento de erros

Todos os erros retornam o formato abaixo:

```json
{
  "error_code": "string",
  "message": "string",
  "field": "string|null"
}
```

Principais códigos:

- `invalid_request`
- `location_not_found`
- `location_ambiguous`
- `gist_not_found`
- `gist_access_denied`
- `gist_comment_not_allowed`
- `integration_contract_error`
- `configuration_error`
- `internal_error`
- `upstream_failure`

Exemplo:

```json
{
  "error_code": "location_not_found",
  "message": "Location not found.",
  "field": null
}
```

---

## Saúde da aplicação

### `GET /health`

Resposta esperada:

```json
{
  "status": "ok"
}
```

---

## Testes

O projeto possui testes para as partes centrais da solução:

- unitários do formatter
- unitários do service
- unitários do adapter do OpenWeather
- testes do SDK OpenWeather
- testes da integração de publicação no Gist
- testes de integração da API HTTP

Para executar:

```bash
make test
```

---

## Estrutura do projeto

```text
src/
├── api/
│   ├── app.py
│   ├── errors.py
│   ├── schemas.py
│   └── routes/
├── integrations/
│   ├── github_gist/
│   └── openweather/
├── shared/
│   ├── exceptions.py
│   └── settings.py
└── weather_comment_publishing/
    ├── adapters/
    ├── formatter.py
    ├── protocols.py
    ├── service.py
    └── types.py
```

---

## Decisões de implementação

- **FastAPI** para a camada HTTP, aproveitando tipagem e validação declarativa;
- **SDK próprio** para encapsular o contrato HTTP do OpenWeatherMap;
- **PyGithub** para integração com comentários em Gist;
- separação entre **integração**, **domínio/aplicação** e **API** para facilitar testes e manutenção;
- uso de **`uv.lock`** para reprodutibilidade do ambiente;
- suporte a **Docker** para execução em ambiente mais próximo de produção.

---

## Observações

- o projeto não implementa autenticação da API, conforme definido no desafio;
- o `gist_id` deve apontar para um Gist existente e acessível pelo token informado;
- o texto final usa a descrição da condição retornada pelo OpenWeatherMap em português quando a API é configurada com `OPENWEATHER_LANGUAGE=pt_br`.
