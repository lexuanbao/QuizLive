"""INV-2: mỗi người chỉ trả lời một lần mỗi câu.

Lần gửi thứ hai cho cùng một câu phải trả 409 và không được làm đổi điểm.
Test cũng kiểm tra schema có UNIQUE(question_id, player_id).
"""

from _support import (
    answer_rows,
    assert_unique_answer_index,
    body,
    correct_index,
    create_room,
    join_player,
    next_question,
    read_state,
    score_sums,
    start_game,
    submit_answer,
)


def test_inv2_lan_gui_thu_hai_bi_tu_choi(client, db_path):
    room = create_room(client)
    code, host_token = room["code"], room["host_token"]

    an = join_player(client, code, "An")
    binh = join_player(client, code, "Binh")
    start_game(client, code, host_token)

    state = read_state(client, code, host_token, "host")
    assert state["status"] == "question", state
    question_id = state["question"]["id"]

    right = correct_index(db_path, question_id)
    wrong = (right + 1) % 4

    first = submit_answer(
        client, code, an["player_token"], question_id, right
    )
    assert first.status_code == 200, first.text
    assert (body(first) or {}).get("accepted") is True, body(first)

    rows = answer_rows(db_path, question_id, an["player_id"])
    assert len(rows) == 1, rows
    points_before = rows[0]["points"]
    choice_before = rows[0]["choice_index"]

    # Bảng answers chắc chắn đã tồn tại sau câu trả lời đầu tiên.
    assert_unique_answer_index(db_path)

    # Bình chưa trả lời nên câu vẫn mở: đây đúng là gửi lần hai cho cùng câu.
    second = submit_answer(
        client, code, an["player_token"], question_id, wrong
    )
    assert second.status_code == 409, (
        "INV-2: gửi lần hai phải trả 409, "
        f"nhận {second.status_code}: {second.text}"
    )

    rows_after = answer_rows(db_path, question_id, an["player_id"])
    assert len(rows_after) == 1, rows_after
    assert rows_after[0]["choice_index"] == choice_before
    assert rows_after[0]["points"] == points_before

    # Bình trả lời để câu đóng, rồi kiểm tra điểm của An vẫn không đổi.
    binh_answer = submit_answer(
        client, code, binh["player_token"], question_id, wrong
    )
    assert binh_answer.status_code == 200, binh_answer.text

    state = read_state(client, code, host_token, "host")
    if state["status"] == "question":
        next_question(client, code, host_token)
        state = read_state(client, code, host_token, "host")
    assert state["status"] in ("reveal", "finished"), state

    player_state = read_state(client, code, an["player_token"], "player")
    by_id, _ = score_sums(db_path, code)
    assert player_state["you"]["score"] == points_before
    assert by_id[str(an["player_id"])] == points_before
