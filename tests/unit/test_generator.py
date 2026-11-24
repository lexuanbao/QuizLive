"""Unit test cho backend/generator.py. Không gọi mạng."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend import generator  # noqa: E402


def _question(**overrides):
    question = {
        "text": "Thủ đô của Pháp là gì?",
        "choices": ["Paris", "Lyon", "Nice", "Marseille"],
        "correct_index": 0,
        "explanation": "Paris là thủ đô của Pháp.",
    }
    question.update(overrides)
    return question


@pytest.fixture
def mock_source(monkeypatch):
    monkeypatch.setenv("QUESTIONS_SOURCE", "mock")
    return monkeypatch


def _assert_valid_set(questions):
    assert isinstance(questions, list)
    assert len(questions) == 5
    for question in questions:
        assert set(question) == {"text", "choices", "correct_index", "explanation"}
        assert isinstance(question["text"], str) and question["text"].strip()
        choices = question["choices"]
        assert isinstance(choices, list) and len(choices) == 4
        assert all(isinstance(choice, str) and choice.strip() for choice in choices)
        assert len({choice.casefold() for choice in choices}) == 4
        assert isinstance(question["correct_index"], int)
        assert 0 <= question["correct_index"] <= 3
        assert isinstance(question["explanation"], str) and question["explanation"].strip()


def test_mock_returns_five_valid_questions(mock_source):
    _assert_valid_set(generator.generate("lịch sử Việt Nam"))


def test_mock_uses_all_answer_positions(mock_source):
    positions = {q["correct_index"] for q in generator.generate("bất kỳ")}
    assert positions == {0, 1, 2, 3}


def test_mock_calls_are_independent(mock_source):
    first = generator.generate("một chủ đề")
    second = generator.generate("chủ đề khác")
    assert first == second
    assert first is not second

    first[0]["text"] = "đã bị sửa"
    first[0]["choices"].append("thêm")
    first.append({"text": "thừa"})
    assert generator.generate("chủ đề khác") == second


def test_mock_is_deterministic(mock_source):
    assert generator.generate("a") == generator.generate("b")


def test_valid_question_accepts_good_question():
    assert generator._valid_question(_question())


@pytest.mark.parametrize(
    "overrides",
    [
        {"text": "   "},
        {"text": None},
        {"choices": ["A", "B", "C"]},
        {"choices": ["A", "B", "C", "D", "E"]},
        {"choices": ["A", "B", "C", ""]},
        {"choices": ["A", "B", "C", "  "]},
        {"choices": ["A", "B", "C", None]},
        {"choices": ["A", "b", "B", "C"]},
        {"choices": ["A", " A ", "B", "C"]},
        {"choices": "A,B,C,D"},
        {"correct_index": 4},
        {"correct_index": -1},
        {"correct_index": "1"},
        {"correct_index": None},
        {"explanation": ""},
        {"explanation": "   "},
        {"explanation": None},
    ],
)
def test_valid_question_rejects_bad_question(overrides):
    assert not generator._valid_question(_question(**overrides))


def test_valid_question_rejects_non_dict():
    assert not generator._valid_question("không phải dict")
    assert not generator._valid_question(None)


def test_collect_drops_invalid_and_strips():
    payload = {
        "questions": [
            _question(text="  Câu tốt  ", choices=[" A ", "B", "C", "D"]),
            _question(choices=["A", "A", "B", "C"]),
            _question(correct_index=7),
            {"text": "thiếu trường"},
        ]
    }
    found = generator._collect(payload)
    assert len(found) == 1
    assert found[0]["text"] == "Câu tốt"
    assert found[0]["choices"] == ["A", "B", "C", "D"]


@pytest.mark.parametrize("payload", [None, [], {}, {"questions": "sai"}, {"questions": [1, 2]}])
def test_collect_tolerates_wrong_shape(payload):
    assert generator._collect(payload) == []


def test_merge_dedupes_by_normalised_text_and_caps_at_five():
    batch = [_question(text=f"Câu {i}") for i in range(4)]
    duplicate = _question(text="  câu   0 ")
    merged = generator._merge(batch + [duplicate] + [_question(text=f"Câu {i}") for i in range(4, 8)])
    assert len(merged) == 5
    assert [q["text"] for q in merged] == ["Câu 0", "Câu 1", "Câu 2", "Câu 3", "Câu 4"]


def test_sanitize_collapses_whitespace_and_newlines():
    assert generator._sanitize_topic("  dòng một\r\nDòng   hai\n\nba  ") == "dòng một Dòng hai ba"


def test_sanitize_cuts_to_eighty_characters():
    result = generator._sanitize_topic("a" * 200)
    assert len(result) == 80
    assert result == "a" * 80


def test_sanitize_cuts_after_collapsing():
    result = generator._sanitize_topic("từ " * 100)
    assert len(result) <= 80
    assert not result.endswith(" ")
    assert "\n" not in result and "\r" not in result


def test_shuffle_choices_keeps_answer_and_choices():
    original = _question(correct_index=2)
    answer = original["choices"][2]
    seen_positions = set()
    for _ in range(50):
        shuffled = generator._shuffle_choices(original)
        assert sorted(shuffled["choices"]) == sorted(original["choices"])
        assert shuffled["choices"][shuffled["correct_index"]] == answer
        seen_positions.add(shuffled["correct_index"])
    assert seen_positions == {0, 1, 2, 3}


def test_llm_retries_once_then_merges(monkeypatch):
    monkeypatch.setenv("QUESTIONS_SOURCE", "llm")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-not-used")
    monkeypatch.setattr(generator, "_client", lambda: object())

    first = {
        "questions": [
            _question(text="Câu 1"),
            _question(text="Câu 2"),
            _question(text="Câu 3"),
            _question(choices=["A", "A", "B", "C"]),
        ]
    }
    second = {
        "questions": [
            _question(text="  câu   3 "),
            _question(text="Câu 4"),
            _question(text="Câu 5"),
            _question(text="Câu 6"),
        ]
    }
    calls = []

    def fake_ask(client, topic):
        calls.append(topic)
        return first if len(calls) == 1 else second

    monkeypatch.setattr(generator, "_ask", fake_ask)
    questions = generator.generate("chủ đề\r\n  có   xuống dòng")

    assert calls == ["chủ đề có xuống dòng"] * 2
    assert [q["text"] for q in questions] == ["Câu 1", "Câu 2", "Câu 3", "Câu 4", "Câu 5"]
    _assert_valid_set(questions)


def test_llm_does_not_retry_when_first_call_is_full(monkeypatch):
    monkeypatch.setenv("QUESTIONS_SOURCE", "llm")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-not-used")
    monkeypatch.setattr(generator, "_client", lambda: object())
    calls = []

    def fake_ask(client, topic):
        calls.append(topic)
        return {"questions": [_question(text=f"Câu {i}") for i in range(5)]}

    monkeypatch.setattr(generator, "_ask", fake_ask)
    assert len(generator.generate("x")) == 5
    assert len(calls) == 1


def test_llm_raises_when_still_too_few(monkeypatch):
    monkeypatch.setenv("QUESTIONS_SOURCE", "llm")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-not-used")
    monkeypatch.setattr(generator, "_client", lambda: object())
    monkeypatch.setattr(
        generator,
        "_ask",
        lambda client, topic: {"questions": [_question(text="Câu 1"), _question(text="Câu 2")]},
    )
    with pytest.raises(RuntimeError, match="not_enough_questions"):
        generator.generate("x")


class _Boom:
    def __init__(self, exc):
        self.chat = self
        self.completions = self
        self._exc = exc

    def create(self, **kwargs):
        raise self._exc


def test_ask_wraps_sdk_errors():
    with pytest.raises(RuntimeError, match="llm_error"):
        generator._ask(_Boom(ConnectionError("mất mạng")), "chủ đề")


def test_ask_wraps_bad_json(monkeypatch):
    from types import SimpleNamespace

    response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="không phải json"))]
    )
    client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(create=lambda **kwargs: response)
        )
    )
    with pytest.raises(RuntimeError, match="llm_error"):
        generator._ask(client, "chủ đề")


def test_missing_api_key_raises(monkeypatch):
    monkeypatch.setenv("QUESTIONS_SOURCE", "llm")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="missing_api_key"):
        generator.generate("bất kỳ")


def test_llm_source_never_reaches_network_without_key(monkeypatch):
    monkeypatch.setenv("QUESTIONS_SOURCE", "llm")
    monkeypatch.setenv("OPENROUTER_API_KEY", "")
    with pytest.raises(RuntimeError, match="missing_api_key"):
        generator.generate("bất kỳ")
