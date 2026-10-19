from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import auth, checks, monitors, overview
from app.core.config import get_settings
from app.demo import mock_api

settings = get_settings()
app = FastAPI(
    title="CloudPulse API",
    version=settings.app_version,
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url=None,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "X-CSRF-Token"],
)

app.include_router(auth.router)
app.include_router(monitors.router)
app.include_router(checks.router)
app.include_router(overview.router)
app.include_router(mock_api.router)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok", "version": settings.app_version, "commit_sha": settings.commit_sha}


frontend_dist = Path(settings.frontend_dist)
assets_dir = frontend_dist / "assets"
if assets_dir.is_dir():
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")


@app.get("/{full_path:path}", include_in_schema=False)
def spa_fallback(full_path: str):
    if full_path.startswith(("api/", "demo/", "docs", "openapi")) or full_path == "health":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found.")
    index_file = frontend_dist / "index.html"
    if not index_file.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Frontend build is not installed.")
    return FileResponse(index_file)
