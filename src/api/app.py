from __future__ import annotations

import os

from fastapi import FastAPI

from src.api.errors import register_exception_handlers
from src.api.routes.github_gist.router import github_gist_router

def create_app() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(github_gist_router)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app

if __name__ == "__main__":
    import uvicorn

    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("HTTP_SERVER_PORT", 8000)))