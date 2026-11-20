"""Tiện ích dùng chung cho ba test bất biến.

Ba luật nằm ở planning/SPEC.md mục 2, định nghĩa chính xác ở
planning/CONTRACT.md. Thư mục này không ai được sửa: test đỏ thì sửa code.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

import pytest

FORBIDDEN_KEYS = {"correct_index", "explanation"}


def require(reason: str) -> None:
    """Skip khi code chưa có; hỏng hẳn khi chạy REQUIRE_INVARIANTS=1."""
    if os.environ.get("REQUIRE_INVARIANTS") == "1":
        pytest.fail(f"REQUIRE_INVARIANTS=1 nhưng {reason}")
    pytest.skip(reason)


def body(response):
    """JSON của response, hoặc None nếu body rỗng/không phải JSON."""
    try:
        return response.json()
    except ValueError:
        return None


def missing_endpoint(response) -> bool:
    """FastAPI trả 404 {"detail": "Not Found"} khi route chưa được viết."""
    if response.status_code != 404:
        return False
    return body(response) == {"detail": "Not Found"}


def _expect(response, expected: int, what: str) -> None:
    assert response.status_code == expected, (
        f"{what}: mong đợi {expected}, nhận {response.status_code}: {response.text}"
    )


def _headers(role: str, token: str) -> dict:
    key = "X-Host-Token" if role == "host" else "X-Player-Token"
    return {key: token}


def create_room(client, topic: str = "Hệ mặt trời") -> dict:
    response = client.post("/api/rooms", json={"topic": topic})
    if missing_endpoint(response):
        require("POST /api/rooms chưa được viết")
    _expect(response, 201, "POST /api/rooms")
    payload = body(response)
    assert isinstance(payload, dict), (
        f"POST /api/rooms: body không phải JSON: {response.text}"
    )
    return payload


def join_player(client, code: str, nickname: str) -> dict:
    response = client.post(f"/api/rooms/{code}/players", json={"nickname": nickname})
    if missing_endpoint(response):
        require("POST /api/rooms/{code}/players chưa được viết")
    _expect(response, 201, f"POST /api/rooms/{code}/players")
    payload = body(response)
    assert isinstance(payload, dict), (
        f"POST /api/rooms/{code}/players: body không phải JSON: {response.text}"
    )
    return payload


def start_game(client, code: str, host_token: str):
    response = client.post(
        f"/api/rooms/{code}/start", headers=_headers("host", host_token)
    )
    if missing_endpoint(response):
        require("POST /api/rooms/{code}/start chưa được viết")
    _expect(response, 200, f"POST /api/rooms/{code}/start")
    return response


def next_question(client, code: str, host_token: str):
    response = client.post(
        f"/api/rooms/{code}/next", headers=_headers("host", host_token)
    )
    if missing_endpoint(response):
        require("POST /api/rooms/{code}/next chưa được viết")
    _expect(response, 200, f"POST /api/rooms/{code}/next")
    return response


def read_state(client, code: str, token: str, role: str) -> dict:
    response = client.get(
        f"/api/rooms/{code}/state",
        params={"role": role},
        headers=_headers(role, token),
    )
    if missing_endpoint(response):
        require(f"GET /api/rooms/{{code}}/state?role={role} chưa được viết")
    _expect(response, 200, f"GET /api/rooms/{code}/state?role={role}")
    payload = body(response)
    assert isinstance(payload, dict), (
        f"GET /api/rooms/{code}/state?role={role}: "
        f"body không phải JSON: {response.text}"
    )
    return payload


def submit_answer(client, code: str, player_token: str, question_id, choice_index: int):
    response = client.post(
        f"/api/rooms/{code}/answers",
        json={"question_id": question_id, "choice_index": choice_index},
        headers=_headers("player", player_token),
    )
    if missing_endpoint(response):
        require("POST /api/rooms/{code}/answers chưa được viết")
    return response


def _connect(db_path):
    path = Path(db_path)
    if not path.exists():
        require(f"chưa có database tại {path}")
    connection = sqlite3.connect(str(path), timeout=5)
    connection.row_factory = sqlite3.Row
    return connection


def query(db_path, sql: str, params=()):
    connection = _connect(db_path)
    try:
        return connection.execute(sql, params).fetchall()
    except sqlite3.OperationalError as exc:
        if "no such table" in str(exc).lower():
            require(f"database chưa có bảng cần dùng: {exc}")
        raise
    finally:
        connection.close()


def correct_index(db_path, question_id) -> int:
    rows = query(
        db_path,
        "SELECT correct_index FROM questions WHERE id = ?",
        (question_id,),
    )
    assert rows, f"không tìm thấy câu hỏi {question_id!r} trong bảng questions"
    return int(rows[0]["correct_index"])


def score_sums(db_path, room_code: str):
    """Trả (điểm theo player_id, điểm theo nickname) tính từ answers."""
    rows = query(
        db_path,
        "SELECT p.id, p.nickname, COALESCE(SUM(a.points), 0) AS total "
        "FROM players p LEFT JOIN answers a ON a.player_id = p.id "
        "WHERE p.room_code = ? GROUP BY p.id, p.nickname",
        (room_code,),
    )
    by_id = {str(row["id"]): row["total"] for row in rows}
    by_nickname = {row["nickname"]: row["total"] for row in rows}
    return by_id, by_nickname


def answer_rows(db_path, question_id, player_id):
    return query(
        db_path,
        "SELECT choice_index, points FROM answers "
        "WHERE question_id = ? AND player_id = ?",
        (question_id, player_id),
    )


def assert_unique_answer_index(db_path) -> None:
    """INV-2: answers phải có UNIQUE(question_id, player_id)."""
    tables = {
        row["name"]
        for row in query(
            db_path, "SELECT name FROM sqlite_master WHERE type = 'table'"
        )
    }
    if "answers" not in tables:
        require("bảng answers chưa được tạo")

    for index in query(db_path, 'PRAGMA index_list("answers")'):
        if not index["unique"]:
            continue
        columns = {
            row["name"]
            for row in query(db_path, f'PRAGMA index_info("{index["name"]}")')
        }
        if columns == {"question_id", "player_id"}:
            return

    pytest.fail("INV-2: bảng answers thiếu UNIQUE(question_id, player_id)")


def assert_no_cumulative_score_column(db_path) -> None:
    """INV-1: chỉ answers.points được mang điểm, không có cột cộng dồn."""
    tables = query(
        db_path,
        "SELECT name FROM sqlite_master "
        "WHERE type = 'table' AND name NOT LIKE 'sqlite_%'",
    )
    offenders = []
    for table in tables:
        name = table["name"]
        for column in query(db_path, f'PRAGMA table_info("{name}")'):
            column_name = column["name"]
            lowered = column_name.lower()
            if (
                name == "answers"
                and "points" in lowered
                and "total" not in lowered
                and "score" not in lowered
            ):
                # Điểm của từng câu trả lời, không phải điểm cộng dồn.
                continue
            if "score" in lowered or "points" in lowered or "total" in lowered:
                offenders.append(f"{name}.{column_name}")

    assert not offenders, (
        "INV-1: có cột có vẻ lưu điểm cộng dồn: " + ", ".join(offenders)
    )


def find_forbidden_keys(payload, path: str = "$"):
    """Tìm correct_index/explanation ở bất kỳ độ sâu nào."""
    found = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            child = f"{path}.{key}"
            if key in FORBIDDEN_KEYS:
                found.append(child)
            found.extend(find_forbidden_keys(value, child))
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            found.extend(find_forbidden_keys(value, f"{path}[{index}]"))
    return found


def assert_no_leak(payload, where: str, status: str) -> None:
    """INV-3: status lobby/question thì không được có khoá đáp án."""
    leaks = find_forbidden_keys(payload)
    assert not leaks, (
        f"INV-3: {where} trả {', '.join(leaks)} khi status={status}"
    )
