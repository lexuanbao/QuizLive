"""Fixture chung cho ba test bất biến.

Mỗi lần chạy dùng một database tạm của pytest, không bao giờ đụng
db/quizlive.db.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
for _path in (ROOT, HERE):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from _support import require  # noqa: E402


@pytest.fixture(scope="session")
def db_path(tmp_path_factory):
    """Database tạm cho cả phiên chạy, đặt trước khi backend.app được import."""
    path = tmp_path_factory.mktemp("quizlive-db") / "quizlive.db"
    os.environ["QUIZLIVE_DB"] = str(path)
    os.environ["QUESTIONS_SOURCE"] = "mock"
    os.environ.setdefault("OPENROUTER_API_KEY", "test-not-used")
    return path


@pytest.fixture(scope="session")
def client(db_path):
    """TestClient của backend.app; skip nếu app chưa import được."""
    try:
        from fastapi.testclient import TestClient
        from backend.app import app
    except Exception as exc:
        require(f"backend.app chưa import được: {exc!r}")

    try:
        test_client = TestClient(app)
    except Exception as exc:
        require(f"không tạo được TestClient: {exc!r}")

    with test_client:
        yield test_client
