PYTHON ?= 3.12
HOST ?= 0.0.0.0
PORT ?= 8000
UV_CACHE_DIR ?= /tmp/.uv-cache
PYTHONPATH ?= .
UV_PROJECT_ENVIRONMENT ?= .venv

.PHONY: help sync run test test-verbose

help:
	@echo "Targets disponíveis:"
	@echo "  make sync          - instala/sincroniza dependências com uv"
	@echo "  make run           - sobe a API FastAPI com uvicorn"
	@echo "  make test          - roda testes unitários com pytest"
	@echo "  make test-verbose  - roda testes unitários com saída detalhada"

sync:
	UV_CACHE_DIR=$(UV_CACHE_DIR) UV_PROJECT_ENVIRONMENT=$(UV_PROJECT_ENVIRONMENT) uv sync --python $(PYTHON) --group dev

run:
	@if [ -f .env ]; then \
		set -a; . ./.env; set +a; \
	fi; \
	PYTHONPATH=$(PYTHONPATH) UV_CACHE_DIR=$(UV_CACHE_DIR) UV_PROJECT_ENVIRONMENT=$(UV_PROJECT_ENVIRONMENT) uv run uvicorn src.api.app:create_app --factory --host $(HOST) --port $${HTTP_SERVER_PORT:-$(PORT)} --reload

test:
	PYTHONPATH=$(PYTHONPATH) UV_CACHE_DIR=$(UV_CACHE_DIR) UV_PROJECT_ENVIRONMENT=$(UV_PROJECT_ENVIRONMENT) uv run pytest tests/unit

test-verbose:
	PYTHONPATH=$(PYTHONPATH) UV_CACHE_DIR=$(UV_CACHE_DIR) UV_PROJECT_ENVIRONMENT=$(UV_PROJECT_ENVIRONMENT) uv run pytest -vv tests/unit
