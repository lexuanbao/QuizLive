"""Endpoint /state. Người 2 phụ trách."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Query, Request

from backend import views

router = APIRouter()

TOKEN_HEADERS = {"host": "X-Host-Token", "player": "X-Player-Token"}


@router.get("/rooms/{code}/state")
def state(
    code: str,
    request: Request,
    role: Literal["host", "player"] = Query(...),
) -> dict:
    """Chỉ đọc token rồi giao việc dựng phản hồi cho views.build_state."""
    token = request.headers.get(TOKEN_HEADERS[role])
    return views.build_state(code, role, token)
