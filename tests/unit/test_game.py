"""Unit test vòng đời phòng, xác thực và nhận câu trả lời. Người 1 phụ trách."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi import HTTPException

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend import db, game  # noqa: E402

FAKE_QUESTIONS = [
    {
        "text": f"Câu số {index}",
        "choices": [f"A{index}", f"B{index}", f"C{index}", f"D{index}"],
        "correct_index": index % 4,
        "explanation": f"Giải thích {index}",
    }
    for index in range(5)
]


# --- tiện ích ----------------------------------------------------------------


def _row(sql: str, params=()):
    connection = db.connect()
    try:
        return connection.execute(sql, params).fetchone()
    finally:
        connection.close()


def _rows(sql: str, params=()):
    connection = db.connect()
    try:
        return connection.execute(sql, params).fetchall()
    finally:
        connection.close()


def _execute(sql: str, params=()) -> None:
    connection = db.connect()
    try:
        connection.execute(sql, params)
        connection.commit()
    finally:
        connection.close()


def _set_opened_at(question_id: str, seconds_ago: int) -> None:
    stamp = (datetime.now(timezone.utc) - timedelta(seconds=seconds_ago)).isoformat()
    _execute("UPDATE questions SET opened_at = ? WHERE id = ?", (stamp, question_id))


def _status(code: str) -> str:
    return _row("SELECT status FROM rooms WHERE code = ?", (code,))["status"]


def _current(code: str):
    return _row(
        "SELECT q.* FROM questions q JOIN rooms r ON r.code = q.room_code "
        "WHERE q.room_code = ? AND q.idx = r.current_index",
        (code,),
    )


def _answer(code: str, player_token: str, question_id: str):
    return _row(
        "SELECT * FROM answers WHERE room_code = ? AND question_id = ? "
        "AND player_id = (SELECT id FROM players WHERE token = ?)",
        (code, question_id, player_token),
    )


def _room_with_players(nicknames: list[str]):
    room = game.create_room("Hệ mặt trời")
    players = [game.join_room(room["code"], name) for name in nicknames]
    return room, players


def _started(nicknames: list[str]):
    room, players = _room_with_players(nicknames)
    game.start_room(room["code"], room["host_token"])
    return room, players


# --- fixture -----------------------------------------------------------------


@pytest.fixture
def fake_questions(monkeypatch, tmp_path):
    monkeypatch.setenv("QUIZLIVE_DB", str(tmp_path / "quizlive.db"))
    monkeypatch.setattr(
        game.generator,
        "generate",
        lambda topic: [dict(item) for item in FAKE_QUESTIONS],
    )
    db.init_db()
    return FAKE_QUESTIONS


# --- create_room -------------------------------------------------------------


def test_create_room_tao_phong_va_cau_hoi(fake_questions):
    result = game.create_room("Hệ mặt trời")

    assert set(result) == {"code", "host_token"}
    assert len(result["code"]) == 6
    assert all(char in game.ALPHABET for char in result["code"])

    room = _row("SELECT * FROM rooms WHERE code = ?", (result["code"],))
    assert room["status"] == "lobby"
    assert room["current_index"] == -1
    assert room["topic"] == "Hệ mặt trời"
    assert room["host_token"] == result["host_token"]

    questions = _rows(
        "SELECT * FROM questions WHERE room_code = ? ORDER BY idx", (result["code"],)
    )
    assert [row["idx"] for row in questions] == [0, 1, 2, 3, 4]
    assert len({row["id"] for row in questions}) == 5
    assert questions[0]["text"] == FAKE_QUESTIONS[0]["text"]
    assert json.loads(questions[0]["choices"]) == FAKE_QUESTIONS[0]["choices"]
    assert questions[0]["correct_index"] == FAKE_QUESTIONS[0]["correct_index"]
    assert questions[0]["opened_at"] is None
    assert questions[0]["closed_at"] is None


def test_create_room_hai_lan_khac_ma(fake_questions):
    codes = {game.create_room("x")["code"] for _ in range(5)}
    assert len(codes) == 5


def test_create_room_thieu_cau_hoi_tra_503(fake_questions, monkeypatch):
    def boom(topic):
        raise RuntimeError("thiếu khoá")

    monkeypatch.setattr(game.generator, "generate", boom)

    with pytest.raises(HTTPException) as info:
        game.create_room("x")

    assert info.value.status_code == 503
    assert info.value.detail == "questions_unavailable"
    assert _row("SELECT COUNT(*) AS n FROM rooms")["n"] == 0


# --- get_room / xác thực -----------------------------------------------------


def test_get_room_khong_co_tra_404(fake_questions):
    with pytest.raises(HTTPException) as info:
        game.get_room("ZZZZZZ")
    assert info.value.status_code == 404
    assert info.value.detail == "room_not_found"


def test_require_host(fake_questions):
    room = game.create_room("x")

    assert game.require_host(room["code"], room["host_token"])["code"] == room["code"]

    for token in (None, "", "sai-token"):
        with pytest.raises(HTTPException) as info:
            game.require_host(room["code"], token)
        assert info.value.status_code == 403
        assert info.value.detail == "forbidden"

    with pytest.raises(HTTPException) as info:
        game.require_host("ZZZZZZ", room["host_token"])
    assert info.value.status_code == 404


def test_require_player(fake_questions):
    room, players = _room_with_players(["An"])

    player = game.require_player(room["code"], players[0]["player_token"])
    assert player["id"] == players[0]["player_id"]

    for token in (None, "", "sai-token"):
        with pytest.raises(HTTPException) as info:
            game.require_player(room["code"], token)
        assert info.value.status_code == 403

    with pytest.raises(HTTPException) as info:
        game.require_player("ZZZZZZ", players[0]["player_token"])
    assert info.value.status_code == 404


# --- join_room ---------------------------------------------------------------


def test_join_room_cat_khoang_trang(fake_questions):
    room = game.create_room("x")
    player = game.join_room(room["code"], "  An  ")

    assert set(player) == {"player_id", "player_token"}
    row = _row("SELECT * FROM players WHERE id = ?", (player["player_id"],))
    assert row["nickname"] == "An"
    assert row["token"] == player["player_token"]
    assert row["joined_at"]


def test_join_room_trung_nickname_tra_409(fake_questions):
    room = game.create_room("x")
    game.join_room(room["code"], "An")

    with pytest.raises(HTTPException) as info:
        game.join_room(room["code"], " An ")
    assert info.value.status_code == 409
    assert info.value.detail == "nickname_taken"
    assert _row("SELECT COUNT(*) AS n FROM players")["n"] == 1


def test_join_room_nickname_rong_tra_422(fake_questions):
    room = game.create_room("x")

    with pytest.raises(HTTPException) as info:
        game.join_room(room["code"], "   ")
    assert info.value.status_code == 422


def test_join_room_phong_khong_ton_tai(fake_questions):
    with pytest.raises(HTTPException) as info:
        game.join_room("ZZZZZZ", "An")
    assert info.value.status_code == 404


def test_join_room_duoc_vao_sau_khi_bat_dau(fake_questions):
    room, _ = _started(["An"])
    player = game.join_room(room["code"], "Binh")
    assert player["player_id"]


# --- start_room / next_question ----------------------------------------------


def test_start_room_mo_cau_dau(fake_questions):
    room, _ = _room_with_players(["An"])

    game.start_room(room["code"], room["host_token"])

    assert _status(room["code"]) == "question"
    stored = _row("SELECT * FROM rooms WHERE code = ?", (room["code"],))
    assert stored["current_index"] == 0
    questions = _rows(
        "SELECT * FROM questions WHERE room_code = ? ORDER BY idx", (room["code"],)
    )
    assert questions[0]["opened_at"] is not None
    assert questions[1]["opened_at"] is None


def test_start_room_lan_hai_tra_409(fake_questions):
    room, _ = _started(["An"])

    with pytest.raises(HTTPException) as info:
        game.start_room(room["code"], room["host_token"])
    assert info.value.status_code == 409
    assert info.value.detail == "already_started"


def test_start_room_sai_token_tra_403(fake_questions):
    room, _ = _room_with_players(["An"])

    with pytest.raises(HTTPException) as info:
        game.start_room(room["code"], "sai")
    assert info.value.status_code == 403
    assert _status(room["code"]) == "lobby"


def test_next_question_khi_cau_dang_mo_tra_409(fake_questions):
    room, _ = _started(["An"])

    with pytest.raises(HTTPException) as info:
        game.next_question(room["code"], room["host_token"])
    assert info.value.status_code == 409
    assert info.value.detail == "question_open"


def test_next_question_sang_cau_ke_tiep(fake_questions):
    room, players = _started(["An", "Binh"])
    first = _current(room["code"])
    _set_opened_at(first["id"], 25)
    game.advance_if_due(room["code"])
    assert _status(room["code"]) == "reveal"

    game.next_question(room["code"], room["host_token"])

    stored = _row("SELECT * FROM rooms WHERE code = ?", (room["code"],))
    assert _status(room["code"]) == "question"
    assert stored["current_index"] == 1
    second = _current(room["code"])
    assert second["idx"] == 1
    assert second["opened_at"] is not None
    assert second["closed_at"] is None


def test_next_question_het_cau_thi_finished(fake_questions):
    room, _ = _started(["An"])

    for _ in range(len(FAKE_QUESTIONS)):
        current = _current(room["code"])
        _set_opened_at(current["id"], 25)
        game.advance_if_due(room["code"])
        game.next_question(room["code"], room["host_token"])

    assert _status(room["code"]) == "finished"
    stored = _row("SELECT * FROM rooms WHERE code = ?", (room["code"],))
    assert stored["current_index"] == len(FAKE_QUESTIONS) - 1


def test_next_question_khi_finished_tra_409(fake_questions):
    room, _ = _started(["An"])
    for _ in range(len(FAKE_QUESTIONS)):
        current = _current(room["code"])
        _set_opened_at(current["id"], 25)
        game.advance_if_due(room["code"])
        game.next_question(room["code"], room["host_token"])

    with pytest.raises(HTTPException) as info:
        game.next_question(room["code"], room["host_token"])
    assert info.value.status_code == 409
    assert info.value.detail == "finished"


# --- seconds_left / advance_if_due -------------------------------------------


def test_seconds_left(fake_questions):
    room, _ = _started(["An"])
    question = _current(room["code"])

    assert game.seconds_left(question) == game.QUESTION_SECONDS
    _set_opened_at(question["id"], 5)
    assert game.seconds_left(_current(room["code"])) == 15
    _set_opened_at(question["id"], 30)
    assert game.seconds_left(_current(room["code"])) == 0
    assert game.seconds_left({"opened_at": None}) == 0
    assert game.seconds_left(None) == 0


def test_advance_if_due_dong_khi_het_gio(fake_questions):
    room, _ = _started(["An", "Binh"])
    question = _current(room["code"])
    _set_opened_at(question["id"], 25)

    game.advance_if_due(room["code"])

    assert _status(room["code"]) == "reveal"
    stored = _row("SELECT * FROM questions WHERE id = ?", (question["id"],))
    assert stored["closed_at"] is not None


def test_advance_if_due_dong_khi_moi_nguoi_da_tra_loi(fake_questions):
    room, players = _started(["An", "Binh"])
    question = _current(room["code"])

    game.submit_answer(room["code"], players[0]["player_token"], question["id"], 0)
    assert _status(room["code"]) == "question"

    game.submit_answer(room["code"], players[1]["player_token"], question["id"], 1)
    assert _status(room["code"]) == "reveal"


def test_advance_if_due_khong_lam_gi_khi_lobby(fake_questions):
    room, _ = _room_with_players(["An"])

    game.advance_if_due(room["code"])

    assert _status(room["code"]) == "lobby"
    assert _current(room["code"]) is None


def test_advance_if_due_idempotent(fake_questions):
    room, _ = _started(["An", "Binh"])
    question = _current(room["code"])
    _set_opened_at(question["id"], 25)
    game.advance_if_due(room["code"])
    closed_at = _row("SELECT closed_at FROM questions WHERE id = ?", (question["id"],))
    assert closed_at["closed_at"] is not None

    game.advance_if_due(room["code"])
    game.advance_if_due(room["code"])

    assert _status(room["code"]) == "reveal"
    again = _row("SELECT closed_at FROM questions WHERE id = ?", (question["id"],))
    assert again["closed_at"] == closed_at["closed_at"]


# --- submit_answer -----------------------------------------------------------


def test_submit_answer_dung_nhanh_duoc_1000(fake_questions):
    room, players = _started(["An", "Binh"])
    question = _current(room["code"])
    _set_opened_at(question["id"], 0)

    game.submit_answer(
        room["code"],
        players[0]["player_token"],
        question["id"],
        question["correct_index"],
    )

    answer = _answer(room["code"], players[0]["player_token"], question["id"])
    assert answer["points"] == 1000
    assert answer["choice_index"] == question["correct_index"]
    assert answer["answered_at"]


def test_submit_answer_sai_duoc_0(fake_questions):
    room, players = _started(["An", "Binh"])
    question = _current(room["code"])

    game.submit_answer(
        room["code"],
        players[0]["player_token"],
        question["id"],
        (question["correct_index"] + 1) % 4,
    )

    answer = _answer(room["code"], players[0]["player_token"], question["id"])
    assert answer["points"] == 0


def test_submit_answer_dung_cham_bi_tru_diem(fake_questions):
    room, players = _started(["An", "Binh"])
    question = _current(room["code"])
    _set_opened_at(question["id"], 10)

    game.submit_answer(
        room["code"],
        players[0]["player_token"],
        question["id"],
        question["correct_index"],
    )

    answer = _answer(room["code"], players[0]["player_token"], question["id"])
    assert answer["points"] == 750


def test_submit_answer_lan_hai_tra_409_va_khong_doi_diem(fake_questions):
    room, players = _started(["An", "Binh"])
    question = _current(room["code"])
    correct = question["correct_index"]
    token = players[0]["player_token"]

    game.submit_answer(room["code"], token, question["id"], correct)
    before = _answer(room["code"], token, question["id"])

    with pytest.raises(HTTPException) as info:
        game.submit_answer(room["code"], token, question["id"], (correct + 1) % 4)

    assert info.value.status_code == 409
    assert info.value.detail == "already_answered"
    after = _answer(room["code"], token, question["id"])
    assert after["points"] == before["points"]
    assert after["choice_index"] == before["choice_index"]
    assert _row("SELECT COUNT(*) AS n FROM answers")["n"] == 1


def test_submit_answer_sau_khi_het_gio_tra_409(fake_questions):
    room, players = _started(["An", "Binh"])
    question = _current(room["code"])
    _set_opened_at(question["id"], 25)

    with pytest.raises(HTTPException) as info:
        game.submit_answer(room["code"], players[0]["player_token"], question["id"], 0)

    assert info.value.status_code == 409
    assert info.value.detail == "question_closed"
    assert _row("SELECT COUNT(*) AS n FROM answers")["n"] == 0
    assert _status(room["code"]) == "reveal"


def test_submit_answer_sai_cau_tra_409(fake_questions):
    room, players = _started(["An", "Binh"])
    other = _row(
        "SELECT * FROM questions WHERE room_code = ? AND idx = 1", (room["code"],)
    )

    with pytest.raises(HTTPException) as info:
        game.submit_answer(room["code"], players[0]["player_token"], other["id"], 0)
    assert info.value.status_code == 409
    assert info.value.detail == "question_closed"

    with pytest.raises(HTTPException) as info:
        game.submit_answer(room["code"], players[0]["player_token"], "khong-co", 0)
    assert info.value.status_code == 409


def test_submit_answer_khi_chua_bat_dau_tra_409(fake_questions):
    room, players = _room_with_players(["An"])
    question = _row(
        "SELECT * FROM questions WHERE room_code = ? AND idx = 0", (room["code"],)
    )

    with pytest.raises(HTTPException) as info:
        game.submit_answer(room["code"], players[0]["player_token"], question["id"], 0)
    assert info.value.status_code == 409


def test_submit_answer_token_sai_tra_403(fake_questions):
    room, _ = _started(["An"])
    question = _current(room["code"])

    with pytest.raises(HTTPException) as info:
        game.submit_answer(room["code"], "sai-token", question["id"], 0)
    assert info.value.status_code == 403
    assert _row("SELECT COUNT(*) AS n FROM answers")["n"] == 0


def test_submit_answer_nguoi_choi_phong_khac_tra_403(fake_questions):
    room, _ = _started(["An"])
    other_room, other_players = _room_with_players(["Binh"])
    question = _current(room["code"])

    with pytest.raises(HTTPException) as info:
        game.submit_answer(
            room["code"], other_players[0]["player_token"], question["id"], 0
        )
    assert info.value.status_code == 403


# --- qr_png ------------------------------------------------------------------


def test_qr_png_tra_anh_png(fake_questions):
    room = game.create_room("x")

    data = game.qr_png(room["code"], "http://testserver/")

    assert isinstance(data, bytes)
    assert data.startswith(b"\x89PNG")


def test_qr_png_phong_khong_ton_tai(fake_questions):
    with pytest.raises(HTTPException) as info:
        game.qr_png("ZZZZZZ", "http://testserver/")
    assert info.value.status_code == 404
