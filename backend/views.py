"""Dựng phản hồi /state, bảng xếp hạng. Người 2 phụ trách."""

from __future__ import annotations

import json
import sqlite3

from backend import db, game

TOP = 10

# Cùng một thứ tự sắp xếp cho bảng xếp hạng và cho hạng của từng người chơi.
_RANKING_SQL = (
    "SELECT p.id, p.nickname, COALESCE(SUM(a.points), 0) AS score "
    "FROM players p LEFT JOIN answers a ON a.player_id = p.id "
    "WHERE p.room_code = ? "
    "GROUP BY p.id "
    "ORDER BY score DESC, p.joined_at ASC, p.nickname ASC"
)

_QUESTION_SQL = (
    "SELECT id, idx, text, choices, correct_index, explanation, "
    "opened_at, closed_at "
    "FROM questions WHERE room_code = ?"
)


def _ranking(
    connection: sqlite3.Connection, room_code: str, limit: int | None = None
) -> list[sqlite3.Row]:
    sql = _RANKING_SQL if limit is None else f"{_RANKING_SQL} LIMIT ?"
    params = (room_code,) if limit is None else (room_code, limit)
    return connection.execute(sql, params).fetchall()


def leaderboard(room_code: str) -> list[dict]:
    """Tối đa 10 người, điểm luôn tính lại từ answers (INV-1)."""
    connection = db.connect()
    try:
        rows = _ranking(connection, room_code, TOP)
    finally:
        connection.close()

    return [
        {"nickname": row["nickname"], "score": int(row["score"]), "rank": rank}
        for rank, row in enumerate(rows, start=1)
    ]


def _question_row(
    connection: sqlite3.Connection,
    room_code: str,
    index: int,
    status: str,
) -> sqlite3.Row | None:
    if status == "finished":
        return connection.execute(
            f"{_QUESTION_SQL} ORDER BY idx DESC LIMIT 1", (room_code,)
        ).fetchone()
    if index < 0:
        return None
    return connection.execute(f"{_QUESTION_SQL} AND idx = ?", (room_code, index)).fetchone()


def _player_names(connection: sqlite3.Connection, room_code: str) -> list[str]:
    rows = connection.execute(
        "SELECT nickname FROM players WHERE room_code = ? "
        "ORDER BY joined_at ASC, nickname ASC",
        (room_code,),
    ).fetchall()
    return [row["nickname"] for row in rows]


def _count_answers(connection: sqlite3.Connection, question_id: str) -> int:
    row = connection.execute(
        "SELECT COUNT(*) FROM answers WHERE question_id = ?", (question_id,)
    ).fetchone()
    return int(row[0])


def _has_answered(
    connection: sqlite3.Connection, question_id: str, player_id: str
) -> bool:
    row = connection.execute(
        "SELECT 1 FROM answers WHERE question_id = ? AND player_id = ?",
        (question_id, player_id),
    ).fetchone()
    return row is not None


def _you(
    connection: sqlite3.Connection,
    room_code: str,
    player_id: str,
    answered_current: bool,
) -> dict:
    """Điểm và hạng của một người chơi, hạng tính trên toàn bộ phòng."""
    rows = _ranking(connection, room_code)
    for rank, row in enumerate(rows, start=1):
        if row["id"] == player_id:
            return {
                "score": int(row["score"]),
                "rank": rank,
                "answered_current": answered_current,
            }
    return {"score": 0, "rank": len(rows) + 1, "answered_current": answered_current}


def build_state(code: str, role: str, token: str | None) -> dict:
    """Phản hồi /state đúng CONTRACT, không lộ đáp án khi câu còn mở (INV-3)."""
    game.advance_if_due(code)
    room = game.get_room(code)

    player = None
    if role == "host":
        game.require_host(code, token)
    elif role == "player":
        player = game.require_player(code, token)

    status = room["status"]
    index = int(room["current_index"])

    connection = db.connect()
    try:
        total = int(
            connection.execute(
                "SELECT COUNT(*) FROM questions WHERE room_code = ?", (code,)
            ).fetchone()[0]
        )
        row = _question_row(connection, code, index, status)
        question_id = row["id"] if row is not None else None
        answered = _count_answers(connection, question_id) if question_id else 0
        answered_current = bool(
            question_id
            and player is not None
            and _has_answered(connection, question_id, player["id"])
        )

        question = None
        if row is not None and status in ("question", "reveal"):
            question = {
                "id": row["id"],
                "index": int(row["idx"]),
                "total": total,
                "text": row["text"],
                "choices": json.loads(row["choices"]),
                "seconds_left": game.seconds_left(row) if status == "question" else 0,
            }

        reveal = None
        if row is not None and status in ("reveal", "finished"):
            reveal = {
                "correct_index": int(row["correct_index"]),
                "explanation": row["explanation"],
            }

        extra: dict = {}
        if role == "host":
            extra["players"] = _player_names(connection, code)
            extra["answered"] = answered
        elif role == "player" and player is not None:
            extra["you"] = _you(connection, code, player["id"], answered_current)
    finally:
        connection.close()

    state: dict = {
        "status": status,
        "question": question,
        "reveal": reveal,
        "leaderboard": leaderboard(code),
    }
    state.update(extra)
    return state
