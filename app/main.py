"""FastAPI entry point. Run with: uvicorn app.main:app"""

from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import __version__, models
from app.config import Settings, load_settings
from app.routes.api import router

STATIC_DIR = Path(__file__).resolve().parent / "static"


def create_app(settings: Settings | None = None, http_client: httpx.Client | None = None) -> FastAPI:
    settings = settings or load_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.settings = settings
        app.state.db = models.connect(settings.db_path)
        app.state.http_client = http_client or httpx.Client(timeout=settings.aw_timeout)
        try:
            yield
        finally:
            app.state.db.close()
            if http_client is None:
                app.state.http_client.close()

    app = FastAPI(title="Presence", version=__version__, lifespan=lifespan)
    app.include_router(router)
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    return app


app = create_app()
