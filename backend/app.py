"""Tạo app, gắn router, phục vụ frontend/."""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# Nap file cau hinh o goc du an vao bien moi truong. Khong ghi de bien da dat
# san, nen test dat QUESTIONS_SOURCE=mock van thang.
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from backend import db  # noqa: E402
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
