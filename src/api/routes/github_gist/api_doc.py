from src.api.schemas import ErrorResponse, PublishWeatherCommentResponse


publish_weather_comment_doc = {
    "summary": "Publica comentário de clima em um Gist",
    "description": (
        "Recebe um alvo de localidade por cidade ou CEP, consulta clima atual e previsão diária, "
        "gera o comentário em português e publica no Gist informado."
    ),
    "response_description": "Comentário publicado com sucesso no Gist.",
    "response_model": PublishWeatherCommentResponse,
    "responses": {
        400: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
    },
    "openapi_extra": {
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
}
