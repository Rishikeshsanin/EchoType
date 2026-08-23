from __future__ import annotations

import csv
import io
import json

import pytest

from echotype.services.history import HistoryStore
from echotype.services.notes import NotesStore
from echotype.services.settings import Settings


def test_history_add_list_edit_delete_and_legacy_compatibility(tmp_path) -> None:
    path = tmp_path / "history.jsonl"
    path.write_text(json.dumps({"text": "legacy transcript", "time": 1}) + "\n", encoding="utf-8")
    store = HistoryStore(path)

    added = store.add({"text": "new transcript has words", "time": 2, "mode": "smart"})
    assert added is not None
    assert [item["text"] for item in store.recent()] == [
        "new transcript has words",
        "legacy transcript",
    ]
    assert store.recent()[0]["word_count"] == 4
    assert store.recent()[1]["id"]

    updated = store.update(str(added["id"]), "edited text")
    assert updated is not None
    assert updated["word_count"] == 2
    assert store.delete(str(added["id"])) is True
    assert [item["text"] for item in store.recent()] == ["legacy transcript"]


@pytest.mark.parametrize(
    ("history_enabled", "private_session"),
    [(False, False), (True, True), (False, True)],
)
def test_history_respects_disabled_and_private_policy(
    tmp_path, history_enabled: bool, private_session: bool
) -> None:
    settings = Settings(tmp_path / "settings.json")
    settings.update({"history_enabled": history_enabled, "private_session": private_session})
    path = tmp_path / "history.jsonl"
    store = HistoryStore(path, settings=settings)

    assert store.add({"text": "must not persist"}) is None
    assert not path.exists()


def test_history_records_configured_language_when_available(tmp_path) -> None:
    settings = Settings(tmp_path / "settings.json")
    settings.set("language", "kn")
    store = HistoryStore(tmp_path / "history.jsonl", settings=settings)

    added = store.add({"text": "ನಮಸ್ಕಾರ"})

    assert added is not None
    assert added["language"] == "Kannada"
    assert added["script"] == "Kannada"


def test_history_query_and_exports(tmp_path) -> None:
    store = HistoryStore(tmp_path / "history.jsonl")
    store.add(
        {
            "text": "Kannada meeting summary",
            "time": 100,
            "language": "Kannada",
            "target": "Writer",
            "mode": "notes",
            "rtf": 0.5,
        }
    )
    store.add({"text": "unrelated", "time": 50, "language": "English"})

    filtered = store.query(text="meeting", language="Kannada", application="Writer", mode="notes")
    assert [item["text"] for item in filtered] == ["Kannada meeting summary"]
    assert "Kannada meeting summary" in store.export_text(filtered)
    rows = list(csv.DictReader(io.StringIO(store.export_csv(filtered))))
    assert rows[0]["mode"] == "notes"
    assert rows[0]["word_count"] == "3"


def test_notes_crud_and_persistence(tmp_path) -> None:
    path = tmp_path / "notes.json"
    store = NotesStore(path)
    created = store.create("Release notes", "First draft")
    updated = store.update(str(created["id"]), body="Second draft")

    assert updated is not None
    assert updated["body"] == "Second draft"
    reloaded = NotesStore(path)
    assert reloaded.get(str(created["id"]))["body"] == "Second draft"  # type: ignore[index]
    assert reloaded.list("second")[0]["title"] == "Release notes"
    assert reloaded.delete(str(created["id"])) is True
    assert reloaded.list() == []


def test_notes_receive_duplicate_and_export(tmp_path) -> None:
    store = NotesStore(tmp_path / "notes.json")
    note = store.receive_dictation(
        "A dictated paragraph.", metadata={"mode": "notes", "language": "English"}
    )
    appended = store.receive_dictation("Another paragraph.", note_id=str(note["id"]))
    duplicate = store.duplicate(str(note["id"]))

    assert appended["body"] == "A dictated paragraph.\n\nAnother paragraph."
    assert appended["source"]["kind"] == "dictation"
    assert duplicate is not None
    assert duplicate["source"]["kind"] == "duplicate"
    assert store.export_markdown(str(note["id"])).startswith("# A dictated paragraph.\n")
    assert "Another paragraph." in store.export_text(str(note["id"]))


def test_notes_atomic_file_has_versioned_format(tmp_path) -> None:
    path = tmp_path / "notes.json"
    NotesStore(path).create(body="Persist me")
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["version"] == NotesStore.FORMAT_VERSION
    assert payload["notes"][0]["body"] == "Persist me"
    assert list(tmp_path.glob("*.tmp")) == []
