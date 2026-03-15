# Runtime image built with uv and locked deps
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

ENV UV_PROJECT_ENVIRONMENT=/app/.venv \
    UV_CACHE_DIR=/root/.cache/uv

WORKDIR /app

# Copy only files needed for dependency resolution first
COPY pyproject.toml uv.lock ./

# Install only prod dependencies (default group) using the locked versions
RUN uv sync --frozen --no-dev

# Copy application source
COPY src ./src

# Final image
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

ENV UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH=/app/.venv/bin:${PATH} \
    PYTHONPATH=/app

WORKDIR /app

# Bring the virtualenv from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY src ./src

# Default command can be overridden by docker-compose
CMD ["uv", "run", "uvicorn", "src.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
