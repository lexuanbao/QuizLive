"""Choi tron van qua API: hai nguoi choi, 5 cau, so bang xep hang voi diem tinh tay.

SPEC muc 10. Dap an lay tu bang questions trong database tam, khong qua API.
"""

from __future__ import annotations

from backend import scoring

from _game_support import (
    answer,
    correct_index,
    create_room,
    join,
    leaks,
    next_q,
    set_opened_at,
    sql,
    start,
    state,
)

# Moi cau: nickname -> (tra loi dung?, so giay da troi qua). Vang mat = khong tra loi.
PLAN = [
    {"Nam": (True, 2), "Lan": (False, 3)},
    {"Nam": (False, 1), "Lan": (True, 4)},
    {"Nam": (True, 6), "Lan": (True, 6)},
    {"Nam": (True, 3)},  # Lan khong tra loi, cau dong vi het gio
    {"Nam": (False, 5), "Lan": (True, 10)},
]


def _expected_scores() -> dict[str, int]:
    totals = {"Nam": 0, "Lan": 0}
    for moves in PLAN:
        for nickname, (correct, seconds) in moves.items():
            totals[nickname] += scoring.points_for(correct, seconds)
    return totals


def _assert_no_leak(client, code, host_token, tokens):
    for role, token in [("host", host_token)] + [("player", t) for t in tokens.values()]:
        payload = state(client, code, role, token)
        assert payload["status"] == "question"
        assert leaks(payload) == [], f"{role} lo dap an: {payload}"


def test_hai_nguoi_choi_tron_5_cau_bang_xep_hang_khop_tinh_tay(client, db_file):
    room = create_room(client)
    code, host = room["code"], room["host_token"]
    tokens = {name: join(client, code, name)["player_token"] for name in ("Nam", "Lan")}

    lobby = state(client, code, "host", host)
    assert lobby["status"] == "lobby" and lobby["question"] is None
    assert lobby["players"] == ["Nam", "Lan"]
    assert leaks(lobby) == []

    assert start(client, code, host).status_code == 200

    for index, moves in enumerate(PLAN):
        current = state(client, code, "host", host)
        question = current["question"]
        assert question["index"] == index and question["total"] == 5
        assert current["answered"] == 0
        right = correct_index(db_file, question["id"])
        _assert_no_leak(client, code, host, tokens)

        for count, (nickname, (correct, seconds)) in enumerate(moves.items(), start=1):
            set_opened_at(db_file, question["id"], seconds)
            choice = right if correct else (right + 1) % 4
            response = answer(client, code, tokens[nickname], question["id"], choice)
            assert response.status_code == 200, response.text
            assert response.json() == {"accepted": True}
            if count < 2:
                _assert_no_leak(client, code, host, tokens)
                assert state(client, code, "host", host)["answered"] == count

        if len(moves) < 2:
            set_opened_at(db_file, question["id"], 25)  # het gio

        revealed = state(client, code, "host", host)
        assert revealed["status"] == "reveal"
        assert revealed["reveal"]["correct_index"] == right
        assert revealed["answered"] == len(moves)

        assert next_q(client, code, host).status_code == 200

    final = state(client, code, "host", host)
    assert final["status"] == "finished"
    assert final["question"] is None
    assert final["players"] == ["Nam", "Lan"]

    expected = _expected_scores()
    order = sorted(expected, key=lambda name: -expected[name])
    assert final["leaderboard"] == [
        {"nickname": name, "score": expected[name], "rank": rank}
        for rank, name in enumerate(order, start=1)
    ]
    for rank, name in enumerate(order, start=1):
        you = state(client, code, "player", tokens[name])["you"]
        assert you["score"] == expected[name]
        assert you["rank"] == rank

    # INV-1: diem luon bang SUM(answers.points).
    rows = sql(
        db_file,
        "SELECT p.nickname, SUM(a.points) AS total FROM players p "
        "JOIN answers a ON a.player_id = p.id WHERE p.room_code = ? GROUP BY p.id",
        (code,),
    )
    assert {row["nickname"]: row["total"] for row in rows} == expected
