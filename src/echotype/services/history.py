from __future__ import annotations

import json
import threading
import time
from pathlib import Path

from echotype.services.settings import HISTORY_PATH


class HistoryStore:
    """Append-only local history with bounded reads and explicit deletion."""

    def __init__(self, path: Path = HISTORY_PATH) -> None:
        self.path = path
        self._lock = threading.RLock()

    def append(self, entry: dict) -> None:
        payload = dict(entry)
        payload.setdefault("time", time.time())
        self.path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(payload, ensure_ascii=False)
        with self._lock:
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")

    def recent(self, limit: int = 200) -> list[dict]:
        if limit <= 0 or not self.path.exists():
            return []
        try:
            with self._lock:
                lines = self.path.read_text(encoding="utf-8").splitlines()[-limit:]
        except OSError:
            return []

        entries: list[dict] = []
        for line in reversed(lines):
            try:
                value = json.loads(line)
            except (ValueError, TypeError):
                continue
            if isinstance(value, dict) and value.get("text"):
                entries.append(value)
        return entries

    def clear(self) -> None:
        with self._lock:
            try:
                self.path.unlink(missing_ok=True)
            except OSError:
                pass
