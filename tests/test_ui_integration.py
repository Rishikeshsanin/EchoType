from __future__ import annotations

import os
from types import SimpleNamespace

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from echotype.app import runtime as runtime_module  # noqa: E402
from echotype.services.history import HistoryStore  # noqa: E402
from echotype.services.notes import NotesStore  # noqa: E402
from echotype.services.settings import Settings  # noqa: E402
from echotype.services.vocabulary import VocabularyService  # noqa: E402
from echotype.ui.main_window import MainWindow  # noqa: E402
from echotype.ui.pages.history import HistoryPage  # noqa: E402
from echotype.ui.pages.notes import NotesPage  # noqa: E402
from echotype.ui.pages.settings import SettingsPage  # noqa: E402
from echotype.ui.pages.vocabulary import VocabularyPage  # noqa: E402


@pytest.fixture(scope="session")
def qt_app() -> QApplication:
    return QApplication.instance() or QApplication([])


class FakeDiagnostics:
    def collect(self) -> dict[str, object]:
        return {"GPU": "Not detected", "Model cache": "Not loaded"}

    def report(self) -> str:
        return "EchoType diagnostics\nNo secrets"


def build_window(tmp_path):
    settings = Settings(tmp_path / "settings.json")
    history = HistoryStore(tmp_path / "history.jsonl", settings=settings)
    notes_store = NotesStore(tmp_path / "notes.json")
    vocabulary = VocabularyService(tmp_path / "vocabulary.json")
    history_page = HistoryPage(history)
    notes_page = NotesPage(store=notes_store, history_store=history)
    settings_page = SettingsPage(
        settings,
        FakeDiagnostics(),
        audio=SimpleNamespace(level=0.0),
        engine=SimpleNamespace(device="cpu", precision="fp32", status="idle"),
        history=history,
    )
    vocabulary_page = VocabularyPage(vocabulary)
    window = MainWindow(
        history_page=history_page,
        notes_page=notes_page,
        settings_page=settings_page,
        vocabulary_page=vocabulary_page,
    )
    return window, history_page, notes_page, notes_store


def test_all_real_pages_mount_and_navigate(qt_app: QApplication, tmp_path) -> None:
    del qt_app
    window, history_page, notes_page, _notes_store = build_window(tmp_path)
    expected = {
        "dictate": window.dictate_page,
        "notes": notes_page,
        "history": history_page,
        "vocabulary": window._vocabulary_page,
        "settings": window._settings_page,
    }
    for key, page in expected.items():
        window.nav_buttons[key].click()
        assert window.pages.currentWidget() is page
        assert window.nav_buttons[key].isChecked()
    window.close()


def test_dictate_send_to_notes_uses_persistent_notes_page(
    qt_app: QApplication, tmp_path
) -> None:
    del qt_app
    window, _history_page, notes_page, notes_store = build_window(tmp_path)
    window.dictate_page.show_transcript(
        "Release candidate note.", {"words": 3, "language_code": "auto"}
    )
    window.dictate_page.transcript_panel.notes_button.click()

    assert notes_store.list()[0]["body"] == "Release candidate note."
    assert window.pages.currentWidget() is notes_page
    window.close()


def test_history_repaste_signal_preserves_text_and_metadata(
    qt_app: QApplication, tmp_path
) -> None:
    del qt_app
    _window, history_page, _notes_page, _notes_store = build_window(tmp_path)
    calls: list[tuple[str, object]] = []
    history_page.repaste_requested.connect(lambda text, entry: calls.append((text, entry)))
    history_page.repaste_requested.emit("Repaste me", {"id": "entry-1"})
    assert calls == [("Repaste me", {"id": "entry-1"})]


def test_runtime_language_selection_persists_and_resets_session(
    qt_app: QApplication, tmp_path, monkeypatch
) -> None:
    del qt_app
    settings = Settings(tmp_path / "settings.json")
    history = HistoryStore(tmp_path / "history.jsonl", settings=settings)
    vocabulary = VocabularyService(tmp_path / "vocabulary.json")
    monkeypatch.setattr(runtime_module, "Settings", lambda: settings)
    monkeypatch.setattr(runtime_module, "HistoryStore", lambda settings=None: history)
    monkeypatch.setattr(
        runtime_module,
        "VocabularyService",
        lambda legacy_terms=None: vocabulary,
    )
    runtime = runtime_module.DictationRuntime()
    resets: list[bool] = []
    runtime.engine.reset_language_memory = lambda: resets.append(True)

    runtime.set_language("te")

    assert Settings(tmp_path / "settings.json").get("language") == "te"
    assert resets == [True]
    assert runtime.ui_snapshot()["language"] == "te"
