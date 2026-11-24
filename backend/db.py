"""Kết nối SQLite, tạo bảng lần đầu.

Đường dẫn database lấy từ biến QUIZLIVE_DB, mặc định db/quizlive.db.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

DEFAULT_DB = "db/quizlive.db"
SCHEMA = Path(__file__).with_name("schema.sql")


def db_path() -> Path:
    return Path(os.environ.get("QUIZLIVE_DB", DEFAULT_DB))


def connect() -> sqlite3.Connection:
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db() -> None:
    """Tạo bảng nếu chưa có. Gọi được nhiều lần."""
    connection = connect()
    try:
        connection.executescript(SCHEMA.read_text(encoding="utf-8"))
        connection.commit()
    finally:
        connection.close()
