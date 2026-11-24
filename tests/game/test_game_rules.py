"""Cac luat ngan qua API: tra loi lan hai, het gio, sai token, phong khong ton tai."""

from __future__ import annotations

from backend import scoring

from _game_support import (
    answer,
    correct_index,
    create_room,
    join,
    next_q,
    set_opened_at,
    sql,
    start,
    state,
)


def _started(client, nicknames=("Nam", "Lan")):
    room = create_room(client)
    tokens = {n: join(client, room["code"], n)["player_token"] for n in nicknames}
    assert start(client, room["code"], room["host_token"]).status_code == 200
    question = state(client, room["code"], "host", room["host_token"])["question"]
    return room, tokens, question


def test_tra_loi_lan_hai_tra_409_va_diem_khong_doi(client, db_file):
    room, tokens, question = _started(client)
    code, qid = room["code"], question["id"]
    right = correct_index(db_file, qid)

    set_opened_at(db_file, qid, 4)
    assert answer(client, code, tokens["Nam"], qid, right).status_code == 200
    stored = "SELECT points FROM answers WHERE question_id = ?"
    before = [r["points"] for r in sql(db_file, stored, (qid,))]
    assert before == [scoring.points_for(True, 4)]

    again = answer(client, code, tokens["Nam"], qid, (right + 1) % 4)
    assert again.status_code == 409
    assert [r["points"] for r in sql(db_file, stored, (qid,))] == before
    you = state(client, code, "player", tokens["Nam"])["you"]
    # Câu còn mở (Lan chưa trả lời) nên điểm chưa hiện, tránh lộ đúng/sai.
    assert you["score"] == 0
    assert you["answered_current"] is True


def test_cau_dang_mo_khong_lo_diem_cho_toi_khi_reveal(client, db_file):
    room, tokens, question = _started(client)
    code, qid = room["code"], question["id"]
    right = correct_index(db_file, qid)

    set_opened_at(db_file, qid, 2)
    assert answer(client, code, tokens["Nam"], qid, right).status_code == 200
    open_state = state(client, code, "player", tokens["Lan"])
    assert open_state["status"] == "question"
    assert all(e["score"] == 0 for e in open_state["leaderboard"])

    assert answer(client, code, tokens["Lan"], qid, (right + 1) % 4).status_code == 200
    revealed = state(client, code, "player", tokens["Nam"])
    assert revealed["status"] == "reveal"
    assert revealed["you"]["score"] == scoring.points_for(True, 2)


def test_bang_diem_thi_dong_hang(client, db_file):
    room, tokens, question = _started(client, ("Nam", "Lan", "Hoa"))
    code, qid = room["code"], question["id"]
    right = correct_index(db_file, qid)

    set_opened_at(db_file, qid, 3)
    for name, choice in (("Nam", right), ("Lan", right), ("Hoa", (right + 1) % 4)):
        assert answer(client, code, tokens[name], qid, choice).status_code == 200

    board = state(client, code, "host", room["host_token"])["leaderboard"]
    points = scoring.points_for(True, 3)
    assert [(e["score"], e["rank"]) for e in board] == [(points, 1), (points, 1), (0, 3)]
    assert state(client, code, "player", tokens["Lan"])["you"]["rank"] == 1
    assert state(client, code, "player", tokens["Hoa"])["you"]["rank"] == 3


def test_het_gio_request_tiep_theo_thay_reveal_va_tra_loi_bi_409(client, db_file):
    room, tokens, question = _started(client)
    code, qid = room["code"], question["id"]

    set_opened_at(db_file, qid, 25)
    after = state(client, code, "player", tokens["Lan"])
    assert after["status"] == "reveal"
    assert after["reveal"]["correct_index"] == correct_index(db_file, qid)

    late = answer(client, code, tokens["Lan"], qid, 0)
    assert late.status_code == 409
    assert state(client, code, "player", tokens["Lan"])["you"]["score"] == 0


def test_het_gio_chan_ca_cau_tra_loi_dau_tien(client, db_file):
    room, tokens, question = _started(client)
    set_opened_at(db_file, question["id"], 25)
    late = answer(client, room["code"], tokens["Nam"], question["id"], 0)
    assert late.status_code == 409


def test_sai_token_tra_403(client):
    room, tokens, question = _started(client)
    code = room["code"]

    assert start(client, code, "sai").status_code == 403
    assert next_q(client, code, "sai").status_code == 403
    assert answer(client, code, "sai", question["id"], 0).status_code == 403
    for role, header in (("host", "X-Host-Token"), ("player", "X-Player-Token")):
        response = client.get(
            f"/api/rooms/{code}/state", params={"role": role}, headers={header: "sai"}
        )
        assert response.status_code == 403
    # Token nguoi choi khong dung duoc cho vai host.
    response = client.get(
        f"/api/rooms/{code}/state",
        params={"role": "host"},
        headers={"X-Host-Token": tokens["Nam"]},
    )
    assert response.status_code == 403


def test_phong_khong_ton_tai_tra_404_room_not_found(client):
    missing = "ZZZZZZ"
    responses = [
        client.post(f"/api/rooms/{missing}/players", json={"nickname": "Nam"}),
        start(client, missing, "x"),
        next_q(client, missing, "x"),
        answer(client, missing, "x", "q", 0),
        client.get(
            f"/api/rooms/{missing}/state",
            params={"role": "host"},
            headers={"X-Host-Token": "x"},
        ),
        client.get(f"/api/rooms/{missing}/qr.png"),
    ]
    for response in responses:
        assert response.status_code == 404, response.request.url
        assert response.json() == {"detail": "room_not_found"}
