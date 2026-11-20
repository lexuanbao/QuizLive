"""INV-3: đáp án không tới trình duyệt khi câu còn mở.

Khi status là lobby hoặc question, phản hồi của mọi endpoint, cho cả host
lẫn người chơi, không được chứa khoá correct_index hay explanation ở bất kỳ
độ sâu nào. Test đi qua toàn bộ ván và kiểm tra sau mỗi bước.
"""

import pytest

from _support import (
    assert_no_leak,
    body,
    create_room,
    join_player,
    next_question,
    read_state,
    start_game,
    submit_answer,
)


def _answer(client, code, player, question_id, choice_index):
    response = submit_answer(
        client, code, player["player_token"], question_id, choice_index
    )
    assert response.status_code == 200, (
        f"trả lời câu {question_id}: nhận {response.status_code}: {response.text}"
    )
    return response


def test_inv3_khong_lo_dap_an_khi_cau_mo(client):
    room = create_room(client)
    assert_no_leak(room, "POST /api/rooms", "lobby")
    code, host_token = room["code"], room["host_token"]

    an = join_player(client, code, "An")
    assert_no_leak(an, "POST /api/rooms/{code}/players", "lobby")
    binh = join_player(client, code, "Binh")

    assert_no_leak(
        read_state(client, code, host_token, "host"),
        "GET /state?role=host",
        "lobby",
    )
    assert_no_leak(
        read_state(client, code, an["player_token"], "player"),
        "GET /state?role=player",
        "lobby",
    )

    started = start_game(client, code, host_token)
    # /start chuyển sang status=question nên body của nó cũng không được lộ đáp án.
    assert_no_leak(body(started), "POST /start", "question")

    answered = set()
    for _ in range(40):
        host_state = read_state(client, code, host_token, "host")
        status = host_state["status"]

        if status == "finished":
            break

        if status == "reveal":
            next_question(client, code, host_token)
            continue

        if status == "lobby":
            pytest.fail("ván đã bắt đầu nhưng trạng thái vẫn là lobby")

        assert status == "question", f"trạng thái không hợp lệ: {status!r}"

        assert_no_leak(host_state, "GET /state?role=host", status)
        assert_no_leak(
            read_state(client, code, an["player_token"], "player"),
            "GET /state?role=player",
            status,
        )
        assert_no_leak(
            read_state(client, code, binh["player_token"], "player"),
            "GET /state?role=player",
            status,
        )

        question_id = host_state["question"]["id"]
        if question_id in answered:
            pytest.fail("câu hỏi không đóng dù cả hai đã trả lời")
        answered.add(question_id)

        first = _answer(client, code, an, question_id, 0)
        assert_no_leak(body(first), "POST /answers", status)

        # An đã trả lời, Bình chưa: câu vẫn mở và vẫn không được lộ đáp án.
        still_open = read_state(client, code, host_token, "host")
        if still_open["status"] == "question":
            assert_no_leak(
                still_open,
                "GET /state?role=host sau khi có người trả lời",
                status,
            )
            assert_no_leak(
                read_state(client, code, an["player_token"], "player"),
                "GET /state?role=player sau khi có người trả lời",
                status,
            )

        duplicate = submit_answer(
            client, code, an["player_token"], question_id, 1
        )
        assert_no_leak(body(duplicate), "POST /answers (lần hai)", status)

        second = _answer(client, code, binh, question_id, 1)
        assert_no_leak(body(second), "POST /answers", status)
    else:
        pytest.fail("ván không kết thúc sau 40 bước")
