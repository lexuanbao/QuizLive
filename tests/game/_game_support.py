"""Tien ich cho test choi tron van: goi API va doc/sua database tam."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

FORBIDDEN_KEYS = {"correct_index", "explanation"}


# --- API -----------------------------------------------------------------------


def create_room(client) -> dict:
    response = client.post("/api/rooms", json={"topic": "He mat troi"})
    assert response.status_code == 201, response.text
    return response.json()


def join(client, code: str, nickname: str) -> dict:
    response = client.post(f"/api/rooms/{code}/players", json={"nickname": nickname})
    assert response.status_code == 201, response.text
    return response.json()


def start(client, code: str, host_token: str):
    return client.post(f"/api/rooms/{code}/start", headers={"X-Host-Token": host_token})


def next_q(client, code: str, host_token: str):
    return client.post(f"/api/rooms/{code}/next", headers={"X-Host-Token": host_token})


def answer(client, code: str, player_token: str, question_id: str, choice: int):
    return client.post(
        f"/api/rooms/{code}/answers",
        json={"question_id": question_id, "choice_index": choice},
        headers={"X-Player-Token": player_token},
    )


def state(client, code: str, role: str, token: str) -> dict:
    header = "X-Host-Token" if role == "host" else "X-Player-Token"
    response = client.get(
        f"/api/rooms/{code}/state", params={"role": role}, headers={header: token}
    )
    assert response.status_code == 200, response.text
    return response.json()


def leaks(payload) -> list[str]:
    """Cac khoa dap an xuat hien o bat ky do sau nao."""
    if isinstance(payload, dict):
        found = [key for key in payload if key in FORBIDDEN_KEYS]
        return found + [k for value in payload.values() for k in leaks(value)]
    if isinstance(payload, list):
        return [k for value in payload for k in leaks(value)]
    return []


# --- database tam ----------------------------------------------------------------


def sql(db_file: Path, query: str, params=()):
    connection = sqlite3.connect(db_file)
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute(query, params).fetchall()
        connection.commit()
        return rows
    finally:
        connection.close()


def correct_index(db_file: Path, question_id: str) -> int:
    rows = sql(db_file, "SELECT correct_index FROM questions WHERE id = ?", (question_id,))
    return int(rows[0]["correct_index"])


def set_opened_at(db_file: Path, question_id: str, seconds_ago: int) -> None:
    stamp = (datetime.now(timezone.utc) - timedelta(seconds=seconds_ago)).isoformat()
    sql(db_file, "UPDATE questions SET opened_at = ? WHERE id = ?", (stamp, question_id))
