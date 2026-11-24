"""Endpoint tạo phòng, vào phòng, trả lời, điều khiển, QR. Người 1 phụ trách."""

from __future__ import annotations

from fastapi import APIRouter, Header, Request, Response
from pydantic import BaseModel, Field

from backend import game

router = APIRouter()


class RoomIn(BaseModel):
    topic: str = Field(min_length=1, max_length=200)


class PlayerIn(BaseModel):
    nickname: str = Field(min_length=1, max_length=24)


class AnswerIn(BaseModel):
    question_id: str
    choice_index: int = Field(ge=0, le=3)


@router.post("/rooms", status_code=201)
def create_room(payload: RoomIn) -> dict:
    return game.create_room(payload.topic)


@router.get("/rooms/{code}/qr.png")
def qr_png(code: str, request: Request) -> Response:
    return Response(
        content=game.qr_png(code, str(request.base_url)),
        media_type="image/png",
    )


@router.post("/rooms/{code}/players", status_code=201)
def join_room(code: str, payload: PlayerIn) -> dict:
    return game.join_room(code, payload.nickname)


@router.post("/rooms/{code}/start")
def start_room(
    code: str,
    host_token: str | None = Header(default=None, alias="X-Host-Token"),
) -> dict:
    game.start_room(code, host_token)
    return {}


@router.post("/rooms/{code}/next")
def next_question(
    code: str,
    host_token: str | None = Header(default=None, alias="X-Host-Token"),
) -> dict:
    game.next_question(code, host_token)
    return {}


@router.post("/rooms/{code}/answers")
def submit_answer(
    code: str,
    payload: AnswerIn,
    player_token: str | None = Header(default=None, alias="X-Player-Token"),
) -> dict:
    game.submit_answer(code, player_token, payload.question_id, payload.choice_index)
    return {"accepted": True}
