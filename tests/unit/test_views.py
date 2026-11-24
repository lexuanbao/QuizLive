"""Unit test cho backend/views.py và backend/routes_state.py. Người 2 phụ trách.

Database tạm qua QUIZLIVE_DB. Dữ liệu chèn thẳng bằng SQL để không phụ thuộc
phần của Người 1; các hàm trong backend/game.py được thay bằng bản giả.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend import db, game, views  # noqa: E402
from backend.routes_state import router as state_router  # noqa: E402

CODE = "ABC234"
HOST_TOKEN = "host-secret"

# Điểm câu 0 của p01..p12. p03/p04 hoà, p10/p11/p12 hoà.
BASE_SCORES = [500, 400, 300, 300, 250, 200, 150, 100, 50, 0, 0, 0]
FORBIDDEN_KEYS = {"correct_index", "explanation"}


def _find_forbidden(payload, path: str = "$") -> list[str]:
    found: list[str] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            child = f"{path}.{key}"
            if key in FORBIDDEN_KEYS:
                found.append(child)
            found.extend(_find_forbidden(value, child))
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            found.extend(_find_forbidden(value, f"{path}[{index}]"))
    return found


@pytest.fixture
def database(tmp_path, monkeypatch):
    monkeypatch.setenv("QUIZLIVE_DB", str(tmp_path / "quizlive.db"))
    db.init_db()
    return tmp_path / "quizlive.db"


def _seed_room(
    code: str = CODE,
    status: str = "question",
    current_index: int = 1,
    questions: int = 5,
    players: int = 12,
) -> None:
    connection = db.connect()
    try:
        connection.execute(
            "INSERT INTO rooms (code, host_token, topic, status, current_index, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (code, HOST_TOKEN, "Hệ mặt trời", status, current_index, "2026-01-01T00:00:00"),
        )
        for index in range(questions):
            connection.execute(
                "INSERT INTO questions "
                "(id, room_code, idx, text, choices, correct_index, explanation, "
                "opened_at, closed_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    f"q{index}",
                    code,
                    index,
                    f"Câu {index + 1}",
                    json.dumps([f"A{index}", f"B{index}", f"C{index}", f"D{index}"]),
                    index % 4,
                    f"Giải thích {index}",
                    "2026-01-01T00:00:00",
                    None,
                ),
            )
        for index in range(1, players + 1):
            connection.execute(
                "INSERT INTO players (id, room_code, nickname, token, joined_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    f"p{index:02d}",
                    code,
                    f"Người {index:02d}",
                    f"tok{index:02d}",
                    f"2026-01-01T00:00:{index:02d}",
                ),
            )
        connection.commit()
    finally:
        connection.close()


def _add_answer(
    question_id: str,
    player_id: str,
    points: int,
    choice: int = 0,
    code: str = CODE,
) -> None:
    connection = db.connect()
    try:
        connection.execute(
            "INSERT INTO answers "
            "(id, room_code, question_id, player_id, choice_index, points, answered_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                f"a-{question_id}-{player_id}",
                code,
                question_id,
                player_id,
                choice,
                points,
                "2026-01-01T00:00:05",
            ),
        )
        connection.commit()
    finally:
        connection.close()


@pytest.fixture
def seeded(database):
    """12 người, câu 0 đã có điểm của tất cả, câu 1 mới có p01 trả lời."""
    _seed_room()
    for index, points in enumerate(BASE_SCORES, start=1):
        _add_answer("q0", f"p{index:02d}", points)
    _add_answer("q1", "p01", 100)
    return database


@pytest.fixture
def fake_game(monkeypatch):
    """Thay các hàm của Người 1; ghi lại thứ tự gọi."""
    calls: list[str] = []

    def get_room(code: str):
        connection = db.connect()
        try:
            row = connection.execute(
                "SELECT * FROM rooms WHERE code = ?", (code,)
            ).fetchone()
        finally:
            connection.close()
        if row is None:
            raise HTTPException(status_code=404, detail="room_not_found")
        return row

    def require_host(code: str, token: str | None):
        row = get_room(code)
        if token != row["host_token"]:
            raise HTTPException(status_code=403, detail="forbidden")
        return row

    def require_player(code: str, token: str | None):
        connection = db.connect()
        try:
            row = connection.execute(
                "SELECT * FROM players WHERE room_code = ? AND token = ?",
                (code, token),
            ).fetchone()
        finally:
            connection.close()
        if row is None:
            raise HTTPException(status_code=403, detail="forbidden")
        return row

    def tracked_get_room(code: str):
        calls.append(f"room:{code}")
        return get_room(code)

    monkeypatch.setattr(
        game, "advance_if_due", lambda code: calls.append(f"advance:{code}"), raising=False
    )
    monkeypatch.setattr(game, "get_room", tracked_get_room, raising=False)
    monkeypatch.setattr(game, "require_host", require_host, raising=False)
    monkeypatch.setattr(game, "require_player", require_player, raising=False)
    monkeypatch.setattr(game, "seconds_left", lambda row: 7, raising=False)
    return calls


def test_leaderboard_tinh_tu_answers_va_gioi_han_10(seeded):
    board = views.leaderboard(CODE)

    assert len(board) == 10
    # Bằng điểm thì đồng hạng: hai người 300 cùng hạng 3, người sau là hạng 5.
    assert [entry["rank"] for entry in board] == [1, 2, 3, 3, 5, 6, 7, 8, 9, 10]
    assert [entry["score"] for entry in board] == [
        600, 400, 300, 300, 250, 200, 150, 100, 50, 0
    ]
    assert board[0] == {"nickname": "Người 01", "score": 600, "rank": 1}
    assert "Người 11" not in [entry["nickname"] for entry in board]
    assert "Người 12" not in [entry["nickname"] for entry in board]


def test_leaderboard_hoa_diem_theo_joined_at_roi_nickname(database):
    _seed_room(code="XYZ234", status="lobby", current_index=-1, players=3)
    connection = db.connect()
    try:
        # Bình vào trước An, cả hai cùng 0 điểm: Bình phải đứng trên.
        connection.execute(
            "UPDATE players SET joined_at = '2026-01-01T00:00:01' WHERE id = 'p02'"
        )
        connection.execute(
            "UPDATE players SET joined_at = '2026-01-01T00:00:02' WHERE id = 'p01'"
        )
        connection.execute(
            "UPDATE players SET nickname = 'An' WHERE id = 'p01'"
        )
        connection.execute(
            "UPDATE players SET nickname = 'Bình' WHERE id = 'p02'"
        )
        connection.commit()
    finally:
        connection.close()

    board = views.leaderboard("XYZ234")
    assert [entry["nickname"] for entry in board] == ["Bình", "An", "Người 03"]
    # Thứ tự hiển thị theo joined_at, nhưng cùng 0 điểm nên cùng hạng 1.
    assert [entry["rank"] for entry in board] == [1, 1, 1]
    assert all(entry["score"] == 0 for entry in board)


def test_state_lobby_host(seeded, fake_game):
    connection = db.connect()
    try:
        connection.execute(
            "UPDATE rooms SET status = 'lobby', current_index = -1 WHERE code = ?",
            (CODE,),
        )
        connection.commit()
    finally:
        connection.close()

    state = views.build_state(CODE, "host", HOST_TOKEN)

    assert state["status"] == "lobby"
    assert state["question"] is None
    assert state["reveal"] is None
    assert state["players"] == [f"Người {index:02d}" for index in range(1, 13)]
    assert state["answered"] == 0
    assert "you" not in state
    assert not _find_forbidden(state)


def test_state_question_host(seeded, fake_game):
    state = views.build_state(CODE, "host", HOST_TOKEN)

    assert state["status"] == "question"
    assert state["question"] == {
        "id": "q1",
        "index": 1,
        "total": 5,
        "text": "Câu 2",
        "choices": ["A1", "B1", "C1", "D1"],
        "seconds_left": 7,
    }
    assert state["reveal"] is None
    assert state["answered"] == 1
    assert len(state["leaderboard"]) == 10
    assert "you" not in state
    assert not _find_forbidden(state)


def test_state_question_player(seeded, fake_game):
    first = views.build_state(CODE, "player", "tok01")
    last = views.build_state(CODE, "player", "tok12")

    assert first["you"] == {"score": 600, "rank": 1, "answered_current": True}
    # Hạng tính trên cả phòng; Người 10, 11, 12 cùng 0 điểm nên đồng hạng 10.
    assert last["you"] == {"score": 0, "rank": 10, "answered_current": False}
    assert len(first["leaderboard"]) == 10
    assert "players" not in first
    assert "answered" not in first
    assert not _find_forbidden(first)


def test_state_reveal_co_dap_an(seeded, fake_game):
    connection = db.connect()
    try:
        connection.execute(
            "UPDATE rooms SET status = 'reveal', current_index = 2 WHERE code = ?",
            (CODE,),
        )
        connection.commit()
    finally:
        connection.close()

    state = views.build_state(CODE, "host", HOST_TOKEN)

    assert state["status"] == "reveal"
    assert state["question"]["index"] == 2
    assert state["question"]["seconds_left"] == 0
    assert state["reveal"] == {"correct_index": 2, "explanation": "Giải thích 2"}


def test_state_finished_dung_cau_cuoi(seeded, fake_game):
    connection = db.connect()
    try:
        connection.execute(
            "UPDATE rooms SET status = 'finished', current_index = 4 WHERE code = ?",
            (CODE,),
        )
        connection.commit()
    finally:
        connection.close()

    state = views.build_state(CODE, "player", "tok12")

    assert state["status"] == "finished"
    assert state["question"] is None
    assert state["reveal"] == {"correct_index": 0, "explanation": "Giải thích 4"}
    assert state["you"]["rank"] == 10


def test_state_goi_advance_if_due_truoc_get_room(seeded, fake_game):
    views.build_state(CODE, "host", HOST_TOKEN)

    assert fake_game[:2] == [f"advance:{CODE}", f"room:{CODE}"]


def test_state_sai_token_bi_tu_choi(seeded, fake_game):
    with pytest.raises(HTTPException) as host_error:
        views.build_state(CODE, "host", "sai")
    assert host_error.value.status_code == 403

    with pytest.raises(HTTPException) as player_error:
        views.build_state(CODE, "player", None)
    assert player_error.value.status_code == 403


@pytest.fixture
def route_client(monkeypatch):
    seen: dict = {}

    def fake_build_state(code: str, role: str, token: str | None) -> dict:
        seen.update(code=code, role=role, token=token)
        return {"status": "lobby", "question": None, "reveal": None, "leaderboard": []}

    monkeypatch.setattr(views, "build_state", fake_build_state)

    app = FastAPI()
    app.include_router(state_router, prefix="/api")
    with TestClient(app) as client:
        yield client, seen


def test_route_doc_token_theo_role(route_client):
    client, seen = route_client

    response = client.get(
        f"/api/rooms/{CODE}/state", params={"role": "host"}, headers={"X-Host-Token": "h1"}
    )
    assert response.status_code == 200
    assert seen == {"code": CODE, "role": "host", "token": "h1"}

    response = client.get(
        f"/api/rooms/{CODE}/state",
        params={"role": "player"},
        headers={"X-Player-Token": "p1"},
    )
    assert response.status_code == 200
    assert seen == {"code": CODE, "role": "player", "token": "p1"}


def test_route_thieu_token_truyen_none(route_client):
    client, seen = route_client

    response = client.get(f"/api/rooms/{CODE}/state", params={"role": "player"})
    assert response.status_code == 200
    assert seen["token"] is None

    # Header của vai kia không được dùng thay.
    response = client.get(
        f"/api/rooms/{CODE}/state",
        params={"role": "host"},
        headers={"X-Player-Token": "p1"},
    )
    assert response.status_code == 200
    assert seen["token"] is None


def test_route_role_khong_hop_le_tra_422(route_client):
    client, _ = route_client

    response = client.get(f"/api/rooms/{CODE}/state", params={"role": "khán giả"})
    assert response.status_code == 422
