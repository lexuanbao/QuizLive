-- Bảng của QuizLive. Không bảng nào lưu điểm cộng dồn (INV-1).
-- Điểm của người chơi luôn là SUM(answers.points).

CREATE TABLE IF NOT EXISTS rooms (
    code          TEXT PRIMARY KEY,
    host_token    TEXT NOT NULL,
    topic         TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'lobby',
    current_index INTEGER NOT NULL DEFAULT -1,
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS questions (
    id            TEXT PRIMARY KEY,
    room_code     TEXT NOT NULL REFERENCES rooms(code),
    idx           INTEGER NOT NULL,
    text          TEXT NOT NULL,
    choices       TEXT NOT NULL,
    correct_index INTEGER NOT NULL,
    explanation   TEXT NOT NULL,
    opened_at     TEXT,
    closed_at     TEXT,
    UNIQUE (room_code, idx)
);

CREATE TABLE IF NOT EXISTS players (
    id         TEXT PRIMARY KEY,
    room_code  TEXT NOT NULL REFERENCES rooms(code),
    nickname   TEXT NOT NULL,
    token      TEXT NOT NULL,
    joined_at  TEXT NOT NULL,
    UNIQUE (room_code, nickname)
);

CREATE TABLE IF NOT EXISTS answers (
    id           TEXT PRIMARY KEY,
    room_code    TEXT NOT NULL REFERENCES rooms(code),
    question_id  TEXT NOT NULL REFERENCES questions(id),
    player_id    TEXT NOT NULL REFERENCES players(id),
    choice_index INTEGER NOT NULL,
    points       INTEGER NOT NULL,
    answered_at  TEXT NOT NULL,
    UNIQUE (question_id, player_id)
);
