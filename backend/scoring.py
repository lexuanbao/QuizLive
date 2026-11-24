"""Công thức điểm. Người 1 phụ trách."""

from __future__ import annotations

BASE_POINTS = 1000
POINTS_PER_SECOND = 25
MAX_SECONDS = 20


def points_for(correct: bool, seconds: int) -> int:
    """Sai -> 0. Đúng -> 1000 - 25*t, t kẹp trong 0..20."""
    if not correct:
        return 0
    clamped = max(0, min(MAX_SECONDS, int(seconds)))
    return BASE_POINTS - POINTS_PER_SECOND * clamped
