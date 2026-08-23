from __future__ import annotations

import json

import pytest

from echotype.core.cleanup import SMART, VERBATIM, clean
from echotype.core.languages import describe
from echotype.services.history import HistoryStore
from echotype.services.settings import Settings


def test_verbatim_mode_preserves_spoken_words() -> None:
    result = clean("  um   actually keep this exactly  ", mode=VERBATIM)
    assert result.text == "um actually keep this exactly"


def test_smart_mode_removes_simple_filler_but_not_meaningful_adverbs() -> None:
    result = clean("um actually this works", mode=SMART)
    assert result.text == "Actually this works"


def test_smart_mode_handles_spoken_punctuation() -> None:
    result = clean("hello comma world full stop", mode=SMART)
    assert result.text == "Hello, world."


def test_custom_vocabulary_restores_product_spelling() -> None:
    result = clean("open echo type", mode=SMART, vocabulary=["EchoType"])
    assert "EchoType" in result.text


def test_shared_script_is_not_presented_as_certain_language_id() -> None:
    info = describe("नमस्ते", "auto")
    assert info["script"] == "DEVANAGARI"
    assert info["is_script_hint"] is True
    assert "Script hint only" in str(info["note"])


def test_settings_persist_outside_runtime_state(tmp_path) -> None:
    path = tmp_path / "settings.json"
    settings = Settings(path)
    settings.set("private_session", True)

    loaded = Settings(path)
    assert loaded.get("private_session") is True
    assert json.loads(path.read_text(encoding="utf-8"))["private_session"] is True


def test_settings_reject_unknown_keys(tmp_path) -> None:
    settings = Settings(tmp_path / "settings.json")
    with pytest.raises(KeyError):
        settings.set("made_up_setting", True)


def test_history_recent_is_newest_first(tmp_path) -> None:
    history = HistoryStore(tmp_path / "history.jsonl")
    history.append({"text": "first", "time": 1})
    history.append({"text": "second", "time": 2})
    assert [item["text"] for item in history.recent()] == ["second", "first"]


def test_history_clear_removes_local_file(tmp_path) -> None:
    history = HistoryStore(tmp_path / "history.jsonl")
    history.append({"text": "private words"})
    history.clear()
    assert history.recent() == []


def test_history_ignores_corrupt_or_textless_records(tmp_path) -> None:
    path = tmp_path / "history.jsonl"
    path.write_text(
        '{"text":"kept","time":2}\nnot-json\n{"time":1}\n[]\n',
        encoding="utf-8",
    )
    assert HistoryStore(path).recent() == [{"text": "kept", "time": 2}]


def test_history_limit_is_bounded_and_newest_first(tmp_path) -> None:
    history = HistoryStore(tmp_path / "history.jsonl")
    for index in range(5):
        history.append({"text": str(index), "time": index})
    assert [entry["text"] for entry in history.recent(limit=2)] == ["4", "3"]
    assert history.recent(limit=0) == []
