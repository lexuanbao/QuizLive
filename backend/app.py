"""Tạo app, gắn router, phục vụ frontend/."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend import db
from backend.routes_game import router as game_router
from backend.routes_state import router as state_router

FRONTEND = Path(__file__).resolve().parents[1] / "frontend"

db.init_db()

app = FastAPI(title="QuizLive")
app.include_router(game_router, prefix="/api")
app.include_router(state_router, prefix="/api")


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}


@app.get("/", include_in_schema=False)
def host_page() -> FileResponse:
    return FileResponse(FRONTEND / "host.html")


@app.get("/play", include_in_schema=False)
def play_page() -> FileResponse:
    return FileResponse(FRONTEND / "play.html")


app.mount("/static", StaticFiles(directory=FRONTEND), name="static")
