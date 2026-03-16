PYTHON ?= 3.12
HOST ?= 0.0.0.0
PORT ?= 8000
UV_CACHE_DIR ?= /tmp/.uv-cache
PYTHONPATH ?= .
UV_PROJECT_ENVIRONMENT ?= .venv
UV_SYNC_FLAGS ?= --frozen --python $(PYTHON)

.PHONY: help sync sync-prod run test test-verbose

help:
	@echo "Targets disponíveis:"
	@echo "  make sync          - instala/sincroniza dependências com uv"
	@echo "  make sync-prod     - instala dependências de produção (sem dev)"
	@echo "  make run           - sobe a API FastAPI com uvicorn"
	@echo "  make test          - roda todos os testes com pytest"
	@echo "  make test-verbose  - roda todos os testes com saída detalhada"

sync:
	UV_CACHE_DIR=$(UV_CACHE_DIR) UV_PROJECT_ENVIRONMENT=$(UV_PROJECT_ENVIRONMENT) uv sync $(UV_SYNC_FLAGS) --group dev

sync-prod:
	UV_CACHE_DIR=$(UV_CACHE_DIR) UV_PROJECT_ENVIRONMENT=$(UV_PROJECT_ENVIRONMENT) uv sync $(UV_SYNC_FLAGS)

run:
	@if [ -f .env ]; then \
		set -a; . ./.env; set +a; \
	fi; \
	PYTHONPATH=$(PYTHONPATH) UV_CACHE_DIR=$(UV_CACHE_DIR) UV_PROJECT_ENVIRONMENT=$(UV_PROJECT_ENVIRONMENT) uv run uvicorn src.api.app:create_app --factory --host $${HTTP_SERVER_HOST:-$(HOST)} --port $${HTTP_SERVER_PORT:-$(PORT)} --reload

test:
	PYTHONPATH=$(PYTHONPATH) UV_CACHE_DIR=$(UV_CACHE_DIR) UV_PROJECT_ENVIRONMENT=$(UV_PROJECT_ENVIRONMENT) uv run pytest tests

test-verbose:
	PYTHONPATH=$(PYTHONPATH) UV_CACHE_DIR=$(UV_CACHE_DIR) UV_PROJECT_ENVIRONMENT=$(UV_PROJECT_ENVIRONMENT) uv run pytest -vv tests

docker:
	docker compose up --build --force-recreate --remove-orphans
