from __future__ import annotations

import json
import os
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from echotype.services.settings import NOTES_PATH


class NotesStore:
    """Crash-safe local note storage with a forward-compatible source payload."""

    FORMAT_VERSION = 1

    def __init__(self, path: Path = NOTES_PATH) -> None:
        self.path = Path(path)
        self._lock = threading.RLock()

    @staticmethod
    def _title_from_body(body: str) -> str:
        first = next(
            (line.strip(" #\t") for line in body.splitlines() if line.strip()), "Untitled note"
        )
        return first[:80]

    @staticmethod
    def _normalise(note: dict[str, Any]) -> dict[str, Any]:
        value = dict(note)
        now = time.time()
        value.setdefault("id", str(uuid.uuid4()))
        value["title"] = str(value.get("title") or "Untitled note").strip() or "Untitled note"
        value["body"] = str(value.get("body") or "")
        value.setdefault("created_at", now)
        value.setdefault("updated_at", value["created_at"])
        value.setdefault("source", {"kind": "manual"})
        return value

    def _read_unlocked(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return []
        raw_notes = payload.get("notes", []) if isinstance(payload, dict) else []
        return [self._normalise(note) for note in raw_notes if isinstance(note, dict)]

    def _write_unlocked(self, notes: list[dict[str, Any]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.path.with_name(f".{self.path.name}.{uuid.uuid4().hex}.tmp")
        payload = json.dumps(
            {"version": self.FORMAT_VERSION, "notes": notes},
            ensure_ascii=False,
            indent=2,
        )
        try:
            with temp_path.open("w", encoding="utf-8", newline="\n") as handle:
                handle.write(payload + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path, self.path)
        finally:
            temp_path.unlink(missing_ok=True)

    def list(self, search: str = "") -> list[dict[str, Any]]:
        with self._lock:
            notes = self._read_unlocked()
        needle = search.casefold().strip()
        if needle:
            notes = [
                note for note in notes if needle in f"{note['title']}\n{note['body']}".casefold()
            ]
        return sorted(notes, key=lambda note: float(note["updated_at"]), reverse=True)

    def get(self, note_id: str) -> dict[str, Any] | None:
        with self._lock:
            return next((note for note in self._read_unlocked() if note["id"] == note_id), None)

    def create(
        self,
        title: str = "",
        body: str = "",
        *,
        source: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        now = time.time()
        clean_body = str(body)
        note = self._normalise(
            {
                "id": str(uuid.uuid4()),
                "title": str(title).strip() or self._title_from_body(clean_body),
                "body": clean_body,
                "created_at": now,
                "updated_at": now,
                "source": dict(source or {"kind": "manual"}),
            }
        )
        with self._lock:
            notes = self._read_unlocked()
            notes.append(note)
            self._write_unlocked(notes)
        return dict(note)

    def update(
        self, note_id: str, *, title: str | None = None, body: str | None = None
    ) -> dict[str, Any] | None:
        with self._lock:
            notes = self._read_unlocked()
            updated = None
            for note in notes:
                if note["id"] != note_id:
                    continue
                if title is not None:
                    note["title"] = str(title).strip() or "Untitled note"
                if body is not None:
                    note["body"] = str(body)
                note["updated_at"] = time.time()
                updated = dict(note)
                break
            if updated is not None:
                self._write_unlocked(notes)
            return updated

    def delete(self, note_id: str) -> bool:
        with self._lock:
            notes = self._read_unlocked()
            remaining = [note for note in notes if note["id"] != note_id]
            if len(remaining) == len(notes):
                return False
            self._write_unlocked(remaining)
            return True

    def duplicate(self, note_id: str) -> dict[str, Any] | None:
        original = self.get(note_id)
        if original is None:
            return None
        return self.create(
            f"{original['title']} (copy)",
            original["body"],
            source={"kind": "duplicate", "note_id": note_id},
        )

    def receive_dictation(
        self,
        text: str,
        *,
        note_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a note or append Dictate/Notes-mode output to an existing note."""
        clean_text = str(text).strip()
        if not clean_text:
            raise ValueError("Dictation text cannot be empty")
        source = {"kind": "dictation", "metadata": dict(metadata or {})}
        if note_id:
            current = self.get(note_id)
            if current is not None:
                separator = "\n\n" if current["body"].strip() else ""
                updated = self.update(note_id, body=f"{current['body']}{separator}{clean_text}")
                if updated is not None:
                    return updated
        return self.create(body=clean_text, source=source)

    def create_from_transcript(self, transcript: dict[str, Any] | str) -> dict[str, Any]:
        if isinstance(transcript, str):
            return self.receive_dictation(transcript)
        metadata = {key: value for key, value in transcript.items() if key != "text"}
        return self.receive_dictation(str(transcript.get("text") or ""), metadata=metadata)

    def export_markdown(self, note_id: str) -> str:
        note = self.get(note_id)
        if note is None:
            raise KeyError(note_id)
        body = note["body"].rstrip()
        return f"# {note['title']}\n\n{body}\n"

    def export_text(self, note_id: str) -> str:
        note = self.get(note_id)
        if note is None:
            raise KeyError(note_id)
        body = note["body"].rstrip()
        return f"{note['title']}\n{'=' * len(note['title'])}\n\n{body}\n"
