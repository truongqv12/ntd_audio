from __future__ import annotations

from collections import deque
from pathlib import Path


def tail_lines(path: str | Path, limit: int = 200) -> list[str]:
    file_path = Path(path)
    if not file_path.exists():
        return []
    with file_path.open("r", encoding="utf-8", errors="replace") as handle:
        return list(deque(handle, maxlen=max(1, min(limit, 2000))))
