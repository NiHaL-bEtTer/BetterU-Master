"""BetterU API entry point.

  /api/...   JSON + streaming API
  everything else: the React web app (apps/web/dist) — website at /, product at /app
"""

import logging
import time
import uuid
from pathlib import Path

from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, select, text

from betteru.config import REPO_ROOT, get_settings
from betteru.db import SessionLocal
from betteru.models import Chunk, Exercise, Food
from betteru.routers import auth, chat, foods, profile, progress, workouts

WEB_DIST = REPO_ROOT / "apps" / "web" / "dist"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("betteru")


def create_app() -> FastAPI:
    settings = get_settings()
    if settings.is_production and (settings.jwt_secret == "change-me-in-production" or len(settings.jwt_secret) < 32):
        raise RuntimeError("Set a strong JWT_SECRET (32+ characters) before running in production.")

    if settings.sentry_dsn:
        import sentry_sdk

        sentry_sdk.init(dsn=settings.sentry_dsn, environment=settings.environment, traces_sample_rate=0.1,
                        send_default_pii=False)

    app = FastAPI(
        title="BetterU API",
        version="3.0.0",
        docs_url=None if settings.is_production else "/api/docs",
        openapi_url="/api/openapi.json",
    )

    if settings.cors_origins and not settings.is_production:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    @app.middleware("http")
    async def request_log(request: Request, call_next):
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            log.exception("request_id=%s %s %s failed", request_id, request.method, request.url.path)
            return JSONResponse({"detail": "Internal server error", "request_id": request_id}, status_code=500)
        response.headers["x-request-id"] = request_id
        if request.url.path.startswith("/api"):
            log.info("request_id=%s %s %s %s %.0fms", request_id, request.method, request.url.path,
                     response.status_code, (time.perf_counter() - start) * 1000)
        return response

    api = APIRouter(prefix="/api")
    for r in (auth, profile, foods, progress, workouts, chat):
        api.include_router(r.router)

    @api.get("/health", tags=["health"])
    def health():
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
            return {
                "status": "ok",
                "foods": db.scalar(select(func.count()).select_from(Food)),
                "knowledge_chunks": db.scalar(select(func.count()).select_from(Chunk)),
                "exercises": db.scalar(select(func.count()).select_from(Exercise)),
                "llm_configured": bool(settings.llm_api_key),
                "web_search": bool(settings.tavily_api_key),
                "recipe_videos": bool(settings.youtube_api_key),
            }

    app.include_router(api)

    # ── Web (one React app: website at /, /about, /team and the product at /app) ──
    if WEB_DIST.exists():
        app.mount("/assets", StaticFiles(directory=WEB_DIST / "assets"), name="web-assets")
        index_html = WEB_DIST / "index.html"
        dist_root = WEB_DIST.resolve()

        @app.get("/{path:path}", include_in_schema=False)
        def web(path: str):
            if path.startswith("api/"):
                return JSONResponse({"detail": "Not Found"}, status_code=404)
            candidate = (WEB_DIST / path).resolve()
            if path and candidate.is_file() and dist_root in candidate.parents:
                return FileResponse(candidate)
            # Client-side routes (/app/log, /about, ...) all load the app shell.
            return FileResponse(index_html, headers={"Cache-Control": "no-cache"})

    return app


app = create_app()


def export_openapi(path: Path) -> None:
    import json

    path.write_text(json.dumps(app.openapi(), indent=2))
