"""Unit test công thức điểm. Người 1 phụ trách."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.scoring import points_for  # noqa: E402


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [(0, 1000), (1, 975), (4, 900), (10, 750), (19, 525), (20, 500)],
)
def test_dung_thi_tru_theo_giay(seconds, expected):
    assert points_for(True, seconds) == expected


@pytest.mark.parametrize("seconds", [0, 3, 20])
def test_sai_thi_bang_khong(seconds):
    assert points_for(False, seconds) == 0


@pytest.mark.parametrize(
    ("seconds", "expected"), [(-10, 1000), (-1, 1000), (21, 500), (99, 500)]
)
def test_giay_duoc_kep_trong_0_20(seconds, expected):
    assert points_for(True, seconds) == expected


def test_tra_ve_int():
    result = points_for(True, 7)
    assert isinstance(result, int)
    assert result == 825
