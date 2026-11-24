"""Vòng đời phòng, nhận câu trả lời. Người 1 phụ trách."""

from __future__ import annotations

import json
import secrets
import sqlite3
from datetime import datetime, timezone
from io import BytesIO
from uuid import uuid4

import qrcode
from fastapi import HTTPException

from backend import db, generator, scoring

ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 6
QUESTION_SECONDS = 20


# --- thời gian ---------------------------------------------------------------


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_iso(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _elapsed_seconds(opened_at: str | None) -> int:
    if not opened_at:
        return 0
    elapsed = int((datetime.now(timezone.utc) - _parse_iso(opened_at)).total_seconds())
    return max(0, min(QUESTION_SECONDS, elapsed))


def seconds_left(question_row) -> int:
    if question_row is None or not question_row["opened_at"]:
        return 0
    elapsed = _elapsed_seconds(question_row["opened_at"])
    return max(0, QUESTION_SECONDS - elapsed)


# --- đọc dữ liệu -------------------------------------------------------------


def get_room(code: str) -> sqlite3.Row:
    connection = db.connect()
    try:
        room = connection.execute(
            "SELECT * FROM rooms WHERE code = ?", (code,)
        ).fetchone()
    finally:
        connection.close()
    if room is None:
        raise HTTPException(status_code=404, detail="room_not_found")
    return room


def _current_question(connection: sqlite3.Connection, room: sqlite3.Row):
    return connection.execute(
        "SELECT * FROM questions WHERE room_code = ? AND idx = ?",
        (room["code"], room["current_index"]),
    ).fetchone()


def _should_close(connection: sqlite3.Connection, room: sqlite3.Row, question) -> bool:
    if seconds_left(question) == 0:
        return True
    players = connection.execute(
        "SELECT COUNT(*) FROM players WHERE room_code = ?", (room["code"],)
    ).fetchone()[0]
    if players == 0:
        return False
    answered = connection.execute(
        "SELECT COUNT(*) FROM answers WHERE question_id = ?", (question["id"],)
    ).fetchone()[0]
    return answered >= players


def advance_if_due(code: str) -> None:
    """Đóng câu đang mở khi hết giờ hoặc mọi người chơi đã trả lời."""
    connection = db.connect()
    try:
        room = connection.execute(
            "SELECT * FROM rooms WHERE code = ?", (code,)
        ).fetchone()
        if room is None or room["status"] != "question":
            return
        question = _current_question(connection, room)
        if question is None or not _should_close(connection, room, question):
            return
        connection.execute(
            "UPDATE rooms SET status = 'reveal' WHERE code = ? AND status = 'question'",
            (code,),
        )
        connection.execute(
            "UPDATE questions SET closed_at = ? WHERE id = ? AND closed_at IS NULL",
            (now_iso(), question["id"]),
        )
        connection.commit()
    finally:
        connection.close()


# --- xác thực ----------------------------------------------------------------


def require_host(code: str, token: str | None) -> sqlite3.Row:
    room = get_room(code)
    if not token or token != room["host_token"]:
        raise HTTPException(status_code=403, detail="forbidden")
    return room


def require_player(code: str, token: str | None) -> sqlite3.Row:
    get_room(code)
    player = None
    if token:
        connection = db.connect()
        try:
            player = connection.execute(
                "SELECT * FROM players WHERE room_code = ? AND token = ?",
                (code, token),
            ).fetchone()
        finally:
            connection.close()
    if player is None:
        raise HTTPException(status_code=403, detail="forbidden")
    return player


# --- vòng đời phòng ----------------------------------------------------------


def _new_code(connection: sqlite3.Connection) -> str:
    while True:
        code = "".join(secrets.choice(ALPHABET) for _ in range(CODE_LENGTH))
        taken = connection.execute(
            "SELECT 1 FROM rooms WHERE code = ?", (code,)
        ).fetchone()
        if taken is None:
            return code


def create_room(topic: str) -> dict:
    try:
        items = generator.generate(topic)
    except RuntimeError:
        raise HTTPException(status_code=503, detail="questions_unavailable") from None

    host_token = secrets.token_urlsafe(24)
    connection = db.connect()
    try:
        code = _new_code(connection)
        connection.execute(
            "INSERT INTO rooms (code, host_token, topic, status, current_index, created_at) "
            "VALUES (?, ?, ?, 'lobby', -1, ?)",
            (code, host_token, topic, now_iso()),
        )
        for idx, item in enumerate(items):
            connection.execute(
                "INSERT INTO questions (id, room_code, idx, text, choices, "
                "correct_index, explanation, opened_at, closed_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, NULL, NULL)",
                (
                    uuid4().hex,
                    code,
                    idx,
                    item["text"],
                    json.dumps(item["choices"], ensure_ascii=False),
                    int(item["correct_index"]),
                    item["explanation"],
                ),
            )
        connection.commit()
    finally:
        connection.close()
    return {"code": code, "host_token": host_token}


def join_room(code: str, nickname: str) -> dict:
    get_room(code)
    cleaned = nickname.strip()
    if not cleaned:
        raise HTTPException(status_code=422, detail="invalid_nickname")

    player_id = uuid4().hex
    player_token = secrets.token_urlsafe(24)
    connection = db.connect()
    try:
        connection.execute(
            "INSERT INTO players (id, room_code, nickname, token, joined_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (player_id, code, cleaned, player_token, now_iso()),
        )
        connection.commit()
    except sqlite3.IntegrityError:
        connection.rollback()
        raise HTTPException(status_code=409, detail="nickname_taken") from None
    finally:
        connection.close()
    return {"player_id": player_id, "player_token": player_token}


def start_room(code: str, token: str | None) -> None:
    room = require_host(code, token)
    if room["status"] != "lobby":
        raise HTTPException(status_code=409, detail="already_started")

    connection = db.connect()
    try:
        connection.execute(
            "UPDATE rooms SET status = 'question', current_index = 0 WHERE code = ?",
            (code,),
        )
        connection.execute(
            "UPDATE questions SET opened_at = ? WHERE room_code = ? AND idx = 0",
            (now_iso(), code),
        )
        connection.commit()
    finally:
        connection.close()


def next_question(code: str, token: str | None) -> None:
    require_host(code, token)
    advance_if_due(code)

    connection = db.connect()
    try:
        room = connection.execute(
            "SELECT * FROM rooms WHERE code = ?", (code,)
        ).fetchone()
        status = room["status"]
        if status == "question":
            raise HTTPException(status_code=409, detail="question_open")
        if status == "finished":
            raise HTTPException(status_code=409, detail="finished")
        if status != "reveal":
            raise HTTPException(status_code=409, detail="not_started")

        last_idx = connection.execute(
            "SELECT MAX(idx) FROM questions WHERE room_code = ?", (code,)
        ).fetchone()[0]
        current = int(room["current_index"])
        if last_idx is not None and current < int(last_idx):
            connection.execute(
                "UPDATE rooms SET status = 'question', current_index = ? WHERE code = ?",
                (current + 1, code),
            )
            connection.execute(
                "UPDATE questions SET opened_at = ? WHERE room_code = ? AND idx = ?",
                (now_iso(), code, current + 1),
            )
        else:
            connection.execute(
                "UPDATE rooms SET status = 'finished' WHERE code = ?", (code,)
            )
        connection.commit()
    finally:
        connection.close()


def submit_answer(
    code: str, token: str | None, question_id: str, choice_index: int
) -> None:
    player = require_player(code, token)
    advance_if_due(code)

    connection = db.connect()
    try:
        room = connection.execute(
            "SELECT * FROM rooms WHERE code = ?", (code,)
        ).fetchone()
        question = connection.execute(
            "SELECT * FROM questions WHERE id = ? AND room_code = ?",
            (question_id, code),
        ).fetchone()
        if (
            question is None
            or room["status"] != "question"
            or int(question["idx"]) != int(room["current_index"])
            or question["closed_at"] is not None
        ):
            raise HTTPException(status_code=409, detail="question_closed")

        points = scoring.points_for(
            int(choice_index) == int(question["correct_index"]),
            _elapsed_seconds(question["opened_at"]),
        )
        try:
            connection.execute(
                "INSERT INTO answers (id, room_code, question_id, player_id, "
                "choice_index, points, answered_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    uuid4().hex,
                    code,
                    question_id,
                    player["id"],
                    int(choice_index),
                    points,
                    now_iso(),
                ),
            )
            connection.commit()
        except sqlite3.IntegrityError:
            # UNIQUE(question_id, player_id): gửi lần hai (INV-2).
            connection.rollback()
            raise HTTPException(status_code=409, detail="already_answered") from None
    finally:
        connection.close()

    advance_if_due(code)


def qr_png(code: str, base_url: str) -> bytes:
    get_room(code)
    image = qrcode.make(f"{base_url}play?code={code}")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()
