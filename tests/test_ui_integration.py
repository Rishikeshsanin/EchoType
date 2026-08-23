from __future__ import annotations

import os
import threading
from types import SimpleNamespace

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from echotype.app import runtime as runtime_module  # noqa: E402
from echotype.core.audio import BLOCK  # noqa: E402
from echotype.core.transcription import Job, Result  # noqa: E402
from echotype.services.history import HistoryStore  # noqa: E402
from echotype.services.notes import NotesStore  # noqa: E402
from echotype.services.settings import Settings  # noqa: E402
from echotype.services.vocabulary import VocabularyService  # noqa: E402
from echotype.ui.main_window import MainWindow  # noqa: E402
from echotype.ui.pages.history import HistoryPage  # noqa: E402
from echotype.ui.pages.notes import NotesPage  # noqa: E402
from echotype.ui.pages.settings import SettingsPage  # noqa: E402
from echotype.ui.pages.vocabulary import VocabularyPage  # noqa: E402
from echotype.ui.theme import stylesheet  # noqa: E402


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


def test_dictate_send_to_notes_uses_persistent_notes_page(qt_app: QApplication, tmp_path) -> None:
    del qt_app
    window, _history_page, notes_page, notes_store = build_window(tmp_path)
    window.dictate_page.show_transcript(
        "Release candidate note.", {"words": 3, "language_code": "auto"}
    )
    window.dictate_page.transcript_panel.notes_button.click()

    assert notes_store.list()[0]["body"] == "Release candidate note."
    assert window.pages.currentWidget() is notes_page
    window.close()


def test_history_repaste_signal_preserves_text_and_metadata(qt_app: QApplication, tmp_path) -> None:
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


def test_product_footer_distinguishes_developer_from_model_credits(
    qt_app: QApplication, tmp_path
) -> None:
    del qt_app
    window, _history_page, _notes_page, _notes_store = build_window(tmp_path)
    footer = window.attribution.text()
    assert "Built by Rishikesh" in footer
    assert "Speech model · SraVaani 1.0" in footer
    assert "ARTPARK-IISc" in footer
    assert "Sharadh Naidu" not in footer
    window.close()


def test_ptt_release_closes_audio_once_with_near_immediate_timeline(
    qt_app: QApplication, tmp_path, monkeypatch
) -> None:
    del qt_app
    settings = Settings(tmp_path / "settings.json")
    settings.update(
        {
            "min_record_seconds": 0.1,
            "auto_copy": False,
            "auto_paste": False,
        }
    )
    history = HistoryStore(tmp_path / "history.jsonl", settings=settings)
    vocabulary = VocabularyService(tmp_path / "vocabulary.json")
    monkeypatch.setattr(runtime_module, "Settings", lambda: settings)
    monkeypatch.setattr(runtime_module, "HistoryStore", lambda settings=None: history)
    monkeypatch.setattr(runtime_module, "VocabularyService", lambda legacy_terms=None: vocabulary)
    monkeypatch.setattr(
        runtime_module,
        "capture_focus",
        lambda: SimpleNamespace(hwnd=41, title="Untitled - Notepad", process_name="python.exe"),
    )
    runtime = runtime_module.DictationRuntime()
    runtime.engine.status = runtime_module.READY
    runtime.engine.model = object()
    runtime.audio._stream = SimpleNamespace(active=True)

    submitted = threading.Event()
    submissions: list[dict[str, object]] = []
    runtime.audio.process = lambda audio: (
        audio,
        {"seconds": audio.size / 16_000.0, "speech_ratio": 1.0},
    )

    def record_submit(*_args, **kwargs):
        submissions.append(dict(kwargs))
        submitted.set()

    runtime.engine.submit = record_submit
    end_calls: list[bool] = []
    original_end = runtime.audio.end

    def counted_end():
        end_calls.append(True)
        return original_end()

    runtime.audio.end = counted_end
    runtime.hotkeys._press(runtime.hotkeys._ptt)
    for _ in range(4):
        runtime.audio._callback(np.full((BLOCK, 1), 0.1, dtype=np.float32), BLOCK, None, None)
    runtime.audio.last_begin_at -= 0.2
    runtime.hotkeys._release(runtime.hotkeys._ptt)
    runtime.hotkeys._release(runtime.hotkeys._ptt)

    assert submitted.wait(1.0)
    assert end_calls == [True]
    assert len(submissions) == 1
    timing = runtime.capture_timing
    ordered = (
        "ptt_key_down",
        "audio_begin",
        "ptt_key_up",
        "end_recording_entry",
        "audio_end_entry",
        "recording_buffer_closed",
        "runtime_recording_false",
        "processing_state",
    )
    assert list(map(timing.get, ordered)) == sorted(timing[name] for name in ordered)
    assert runtime.capture_stop_latency_ms is not None
    assert runtime.capture_stop_latency_ms < 50.0

    submitted.clear()
    states: list[tuple[str, str]] = []
    runtime.recording_state.connect(lambda state, detail: states.append((state, detail)))
    settings.set("min_record_seconds", 0.35)
    runtime.hotkeys._press(runtime.hotkeys._ptt)
    runtime.hotkeys._release(runtime.hotkeys._ptt)
    assert not submitted.wait(0.05)
    assert end_calls == [True, True]
    assert len(submissions) == 1
    assert any(state == "ready" and "Clip too short" in detail for state, detail in states)

    submitted.clear()
    settings.set("min_record_seconds", 0.1)
    runtime.hotkeys._press(runtime.hotkeys._ptt)
    runtime.audio.last_begin_at -= 0.2
    runtime.hotkeys._press(runtime.hotkeys._toggle)
    runtime.hotkeys._release(runtime.hotkeys._ptt)
    assert submitted.wait(1.0)
    assert end_calls == [True, True, True]
    assert len(submissions) == 2

    submitted.clear()
    runtime.hotkeys._press(runtime.hotkeys._ptt)
    runtime.audio.last_begin_at -= 0.2
    runtime.hotkeys._press(runtime.hotkeys._cancel)
    runtime.hotkeys._release(runtime.hotkeys._ptt)
    assert not submitted.wait(0.05)
    assert end_calls == [True, True, True]
    assert len(submissions) == 2
    assert any(state == "ready" and detail == "Recording cancelled" for state, detail in states)


def test_echotype_owned_window_is_never_selected_as_external_target() -> None:
    external = SimpleNamespace(hwnd=41, title="Untitled - Notepad")
    own_window = SimpleNamespace(hwnd=99, title="EchoType")

    assert runtime_module.external_capture_target(external, {99}, None) is external
    assert runtime_module.external_capture_target(own_window, {99}, external) is external


@pytest.mark.parametrize("theme", ["dark", "light", "system"])
@pytest.mark.parametrize("size", [(940, 640), (1280, 800), (1366, 768), (1600, 900)])
def test_release_layout_and_theme_offscreen_smoke(
    qt_app: QApplication, tmp_path, theme: str, size: tuple[int, int]
) -> None:
    previous = qt_app.styleSheet()
    qt_app.setStyleSheet(stylesheet(theme))
    window, _history_page, _notes_page, _notes_store = build_window(tmp_path)
    window.resize(*size)
    window.apply_runtime_snapshot(
        {
            "language": "te",
            "mode": "smart",
            "hotkey_ptt": "Right Shift",
            "hotkey_toggle": "F9",
            "hotkey_paste_last": "F11",
            "hotkey_cancel": "Esc",
            "history": [],
        }
    )
    window.show()
    qt_app.processEvents()

    assert window.size().width() == size[0]
    assert window.size().height() == size[1]
    assert window.dictate_page.transcript_panel.width() > 300
    assert window.dictate_page.recording.width() >= 250
    assert all(
        label.width() > 0 for label in window.dictate_page.recording.shortcut_keycaps.values()
    )
    assert window.dictate_page.language_selector.combo.currentText() == "Telugu"

    window.close()
    qt_app.setStyleSheet(previous)


def test_result_uses_language_captured_for_job_not_new_setting(
    qt_app: QApplication, tmp_path, monkeypatch
) -> None:
    del qt_app
    settings = Settings(tmp_path / "settings.json")
    settings.update(
        {
            "language": "en",
            "history_enabled": False,
            "auto_copy": False,
            "auto_paste": False,
        }
    )
    history = HistoryStore(tmp_path / "history.jsonl", settings=settings)
    vocabulary = VocabularyService(tmp_path / "vocabulary.json")
    monkeypatch.setattr(runtime_module, "Settings", lambda: settings)
    monkeypatch.setattr(runtime_module, "HistoryStore", lambda settings=None: history)
    monkeypatch.setattr(runtime_module, "VocabularyService", lambda legacy_terms=None: vocabulary)
    runtime = runtime_module.DictationRuntime()
    emitted: list[dict[str, object]] = []
    runtime.transcript_ready.connect(lambda _text, metadata: emitted.append(dict(metadata)))
    job = Job(
        np.ones(16_000, dtype=np.float32),
        {"seconds": 1.0},
        mode="smart",
        language="te",
    )

    runtime._on_engine_result(Result("తెలుగు", "తెలుగు", job, 0.2))

    assert emitted[0]["language_code"] == "te"
    assert emitted[0]["language_name"] == "Telugu"
