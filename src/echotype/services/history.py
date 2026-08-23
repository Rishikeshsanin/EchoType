from __future__ import annotations

import csv
import io
import json
import os
import threading
import time
import uuid
from collections.abc import Iterable
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from echotype.core.languages import AUTO, describe, name_for_code
from echotype.services.settings import HISTORY_PATH


class HistoryStore:
    """Local JSONL transcript history with backward-compatible record mutation.

    Existing history lines are left untouched until a mutation is requested.
    Rewrites use an atomic replace, and legacy records gain IDs only in the
    rewritten file. Passing Settings makes privacy policy enforcement a service
    invariant instead of relying solely on callers.
    """

    def __init__(self, path: Path = HISTORY_PATH, settings: Any | None = None) -> None:
        self.path = Path(path)
        self.settings = settings
        self._lock = threading.RLock()

    def _recording_allowed(self) -> bool:
        if self.settings is None:
            return True
        return bool(self.settings.get("history_enabled", True)) and not bool(
            self.settings.get("private_session", False)
        )

    @staticmethod
    def _word_count(text: str) -> int:
        return len(text.split())

    @staticmethod
    def _record_id(value: dict[str, Any], index: int) -> str:
        existing = str(value.get("id") or "").strip()
        if existing:
            return existing
        # Deterministic for unchanged legacy files, so UI selections are stable.
        fingerprint = json.dumps(value, ensure_ascii=False, sort_keys=True)
        return str(uuid.uuid5(uuid.NAMESPACE_URL, f"echotype-history:{index}:{fingerprint}"))

    def _normalise(self, value: dict[str, Any], index: int) -> dict[str, Any]:
        item = dict(value)
        item["id"] = self._record_id(item, index)
        timestamp = item.get("time", item.get("timestamp", item.get("created_at", 0.0)))
        try:
            item["time"] = float(timestamp)
        except (TypeError, ValueError):
            item["time"] = 0.0
        text = str(item.get("text") or "")
        item["text"] = text
        item.setdefault("word_count", self._word_count(text))
        if not item.get("script") and text:
            language_info = describe(text)
            if language_info.get("script_label") != "Unknown":
                item["script"] = language_info.get("script_label")
        return item

    def _read_unlocked(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        try:
            lines = self.path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return []
        entries: list[dict[str, Any]] = []
        for index, line in enumerate(lines):
            try:
                value = json.loads(line)
            except (ValueError, TypeError):
                continue
            if isinstance(value, dict) and value.get("text"):
                entries.append(self._normalise(value, index))
        return entries

    def _write_unlocked(self, entries: Iterable[dict[str, Any]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.path.with_name(f".{self.path.name}.{uuid.uuid4().hex}.tmp")
        payload = "".join(
            json.dumps(dict(entry), ensure_ascii=False, separators=(",", ":")) + "\n"
            for entry in entries
        )
        try:
            with temp_path.open("w", encoding="utf-8", newline="\n") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path, self.path)
        finally:
            temp_path.unlink(missing_ok=True)

    def append(self, entry: dict[str, Any]) -> dict[str, Any] | None:
        """Append a transcript, or return None when history policy forbids it."""
        if not self._recording_allowed():
            return None
        payload = dict(entry)
        text = str(payload.get("text") or "").strip()
        if not text:
            raise ValueError("History text cannot be empty")
        payload["text"] = text
        payload.setdefault("id", str(uuid.uuid4()))
        payload.setdefault("time", time.time())
        payload.setdefault("word_count", self._word_count(text))
        if self.settings is not None and not payload.get("language"):
            selected_language = str(self.settings.get("language", AUTO) or AUTO)
            if selected_language != AUTO:
                payload["language"] = name_for_code(selected_language)
        if not payload.get("script"):
            language_info = describe(text)
            if language_info.get("script_label") != "Unknown":
                payload["script"] = language_info.get("script_label")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        with self._lock, self.path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(line + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        return dict(payload)

    add = append

    def recent(self, limit: int = 200) -> list[dict[str, Any]]:
        if limit <= 0:
            return []
        with self._lock:
            entries = self._read_unlocked()
        return sorted(entries, key=lambda item: float(item.get("time", 0.0)), reverse=True)[:limit]

    list = recent

    def get(self, record_id: str) -> dict[str, Any] | None:
        with self._lock:
            return next(
                (item for item in self._read_unlocked() if item["id"] == record_id),
                None,
            )

    def update(self, record_id: str, text: str) -> dict[str, Any] | None:
        clean_text = str(text).strip()
        if not clean_text:
            raise ValueError("History text cannot be empty")
        with self._lock:
            entries = self._read_unlocked()
            updated = None
            for item in entries:
                if item["id"] == record_id:
                    item["text"] = clean_text
                    item["word_count"] = self._word_count(clean_text)
                    language_info = describe(clean_text)
                    script = language_info.get("script_label")
                    if script and script != "Unknown":
                        item["script"] = script
                    else:
                        item.pop("script", None)
                    item["edited_at"] = time.time()
                    updated = dict(item)
                    break
            if updated is not None:
                self._write_unlocked(entries)
            return updated

    def delete(self, record_id: str) -> bool:
        with self._lock:
            entries = self._read_unlocked()
            remaining = [item for item in entries if item["id"] != record_id]
            if len(remaining) == len(entries):
                return False
            if remaining:
                self._write_unlocked(remaining)
            else:
                self.path.unlink(missing_ok=True)
            return True

    def clear(self) -> None:
        with self._lock:
            self.path.unlink(missing_ok=True)

    def query(
        self,
        *,
        text: str = "",
        date_from: date | datetime | None = None,
        language: str = "",
        application: str = "",
        mode: str = "",
        limit: int = 10_000,
    ) -> list[dict[str, Any]]:
        needle = text.casefold().strip()
        language_key = language.casefold().strip()
        app_key = application.casefold().strip()
        mode_key = mode.casefold().strip()
        if isinstance(date_from, datetime):
            minimum_time = date_from.timestamp()
        elif isinstance(date_from, date):
            minimum_time = datetime.combine(date_from, datetime.min.time()).timestamp()
        else:
            minimum_time = None

        results = []
        for item in self.recent(limit):
            haystack = " ".join(
                str(item.get(key) or "")
                for key in ("text", "target", "application", "language", "script")
            ).casefold()
            item_language = str(item.get("language") or item.get("script") or "").casefold()
            item_app = str(item.get("target") or item.get("application") or "").casefold()
            item_mode = str(item.get("mode") or "").casefold()
            if needle and needle not in haystack:
                continue
            if minimum_time is not None and float(item.get("time", 0.0)) < minimum_time:
                continue
            if language_key and language_key != item_language:
                continue
            if app_key and app_key != item_app:
                continue
            if mode_key and mode_key != item_mode:
                continue
            results.append(item)
        return results

    def export_text(self, entries: Iterable[dict[str, Any]] | None = None) -> str:
        records = list(entries) if entries is not None else self.recent(10_000)
        blocks = []
        for item in records:
            try:
                timestamp = datetime.fromtimestamp(
                    float(item.get("time", 0.0)), tz=UTC
                ).astimezone()
            except (OSError, OverflowError, TypeError, ValueError):
                timestamp = datetime.fromtimestamp(0, tz=UTC)
            meta = [timestamp.isoformat(timespec="seconds")]
            for key in ("language", "script", "mode", "target"):
                if item.get(key):
                    meta.append(str(item[key]))
            blocks.append(f"[{' | '.join(meta)}]\n{item.get('text', '')}")
        return "\n\n".join(blocks) + ("\n" if blocks else "")

    def export_csv(self, entries: Iterable[dict[str, Any]] | None = None) -> str:
        records = list(entries) if entries is not None else self.recent(10_000)
        output = io.StringIO(newline="")
        fields = [
            "id",
            "time",
            "text",
            "language",
            "script",
            "mode",
            "target",
            "word_count",
            "elapsed",
            "rtf",
            "audio_seconds",
        ]
        writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for item in records:
            writer.writerow(item)
        return output.getvalue()
