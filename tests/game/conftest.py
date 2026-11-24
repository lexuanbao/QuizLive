"""Fixture cho test choi tron van qua API.

Moi test mot database tam trong tmp_path, khong dung db/quizlive.db.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def db_file(tmp_path, monkeypatch) -> Path:
    path = tmp_path / "quizlive.db"
    monkeypatch.setenv("QUIZLIVE_DB", str(path))
    monkeypatch.setenv("QUESTIONS_SOURCE", "mock")
    return path


@pytest.fixture
def client(db_file):
    """TestClient cua backend.app, import lai sau khi dat QUIZLIVE_DB.

    backend.app goi db.init_db() luc import. Bo module khoi sys.modules truoc
    va sau test de lan import sau (o test khac) lai tao bang dung database.
    """
    from fastapi.testclient import TestClient

    sys.modules.pop("backend.app", None)
    from backend.app import app

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        sys.modules.pop("backend.app", None)
