"""INV-1: điểm luôn tính lại được từ bảng answers.

Không có chỗ nào cộng dồn điểm riêng. Điểm của một người chơi phải bằng
SUM(answers.points) của người đó, và bảng xếp hạng cũng phải khớp với tổng
tính từ answers. Test kiểm tra cả schema (không có cột điểm cộng dồn) lẫn
hành vi qua API.
"""

import pytest

from _support import (
    assert_no_cumulative_score_column,
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


def _answer(client, code, player, question_id, choice_index):
    response = submit_answer(
        client, code, player["player_token"], question_id, choice_index
    )
    assert response.status_code == 200, (
        f"trả lời câu {question_id}: nhận {response.status_code}: {response.text}"
    )
    assert (body(response) or {}).get("accepted") is True, body(response)


def _player_state(client, code, player):
    return read_state(client, code, player["player_token"], "player")


def _check_leaderboard(leaderboard, by_nickname, where):
    for entry in leaderboard:
        nickname = entry["nickname"]
        assert nickname in by_nickname, f"{where}: {leaderboard}"
        assert entry["score"] == by_nickname[nickname], (
            f"{where}: ghi {nickname}={entry['score']} nhưng "
            f"SUM(answers.points)={by_nickname[nickname]}"
        )


def _check_final(client, code, host_token, players, by_id, by_nickname):
    state = read_state(client, code, host_token, "host")
    assert state["status"] == "finished", state
    leaderboard = state["leaderboard"]

    assert len(leaderboard) == len(players), leaderboard
    assert [entry["rank"] for entry in leaderboard] == list(
        range(1, len(players) + 1)
    ), leaderboard

    _check_leaderboard(leaderboard, by_nickname, "bảng xếp hạng cuối ván")

    assert leaderboard[0]["score"] > leaderboard[-1]["score"]

    for player, nickname in players:
        player_state = _player_state(client, code, player)
        assert player_state["you"]["score"] == by_id[str(player["player_id"])], (
            f"điểm của {nickname} không bằng SUM(answers.points)"
        )
        expected_rank = next(
            entry["rank"]
            for entry in leaderboard
            if entry["nickname"] == nickname
        )
        assert player_state["you"]["rank"] == expected_rank


def test_inv1_diem_bang_tong_answers(client, db_path):
    room = create_room(client)
    code, host_token = room["code"], room["host_token"]

    an = join_player(client, code, "An")
    binh = join_player(client, code, "Binh")
    players = [(an, "An"), (binh, "Binh")]
    start_game(client, code, host_token)

    checked_schema = False
    answered = set()
    for _ in range(40):
        state = read_state(client, code, host_token, "host")
        status = state["status"]

        if status == "question":
            question_id = state["question"]["id"]
            if question_id in answered:
                pytest.fail("câu hỏi không đóng dù cả hai đã trả lời")
            answered.add(question_id)

            right = correct_index(db_path, question_id)
            _answer(client, code, an, question_id, right)
            _answer(client, code, binh, question_id, (right + 1) % 4)

            if not checked_schema:
                # Bảng answers chắc chắn đã tồn tại sau câu trả lời đầu tiên.
                assert_no_cumulative_score_column(db_path)
                checked_schema = True
            continue

        if status == "lobby":
            pytest.fail("ván đã bắt đầu nhưng trạng thái vẫn là lobby")

        if status in ("reveal", "finished"):
            by_id, by_nickname = score_sums(db_path, code)
            _check_leaderboard(
                state["leaderboard"], by_nickname, "bảng xếp hạng giữa ván"
            )
            for player, nickname in players:
                player_state = _player_state(client, code, player)
                assert player_state["you"]["score"] == by_id[str(player["player_id"])], (
                    f"điểm của {nickname} không bằng SUM(answers.points)"
                )

            if status == "finished":
                _check_final(
                    client, code, host_token, players, by_id, by_nickname
                )
                break

            next_question(client, code, host_token)
            continue

        pytest.fail(f"trạng thái không hợp lệ: {status!r}")
    else:
        pytest.fail("ván không kết thúc sau 40 bước")
