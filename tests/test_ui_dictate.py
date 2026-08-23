from __future__ import annotations

import os
from types import SimpleNamespace

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from echotype.core.languages import LANGUAGES  # noqa: E402
from echotype.ui.pages.dictate import DictatePage  # noqa: E402
from echotype.ui.widgets.language_selector import LanguageSelector  # noqa: E402
from echotype.ui.widgets.transcript_panel import TranscriptPanel  # noqa: E402


@pytest.fixture(scope="session")
def qt_app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_language_selector_contains_complete_backend_catalog(qt_app: QApplication) -> None:
    del qt_app
    selector = LanguageSelector()
    ui_codes = {
        str(selector.combo.itemData(index))
        for index in range(selector.combo.count())
        if selector.combo.itemData(index)
    }
    backend_codes = {code for code, _name, _script, _primary in LANGUAGES}
    assert ui_codes == backend_codes
    assert selector.combo.itemData(0) == "auto"


def test_manual_language_selection_explains_script_constraint(qt_app: QApplication) -> None:
    del qt_app
    selector = LanguageSelector()
    selector.set_language("mr")
    assert selector.language_code == "mr"
    assert "Marathi selected" in selector.hint.text()
    assert "Devanagari script" in selector.hint.text()


def test_language_dropdown_is_grouped_searchable_and_rejects_invalid_input(
    qt_app: QApplication,
) -> None:
    del qt_app
    selector = LanguageSelector()
    selector.set_language("te")
    selector.combo.lineEdit().setText("not a supported language")
    selector._accept_typed_name()

    labels = [selector.combo.itemText(index) for index in range(selector.combo.count())]
    assert labels[0] == "Auto-detect"
    assert labels.index("POPULAR") < labels.index("English")
    assert labels.index("ALL LANGUAGES") < labels.index("Angami")
    assert selector.combo.isEditable()
    assert selector.combo.accessibleName() == "Dictation language"
    assert selector.language_code == "te"
    assert selector.combo.currentText() == "Telugu"
    selector.combo.completer().setCompletionPrefix("lugu")
    assert selector.combo.completer().completionCount() == 1
    assert selector.combo.completer().currentCompletion() == "Telugu"


def test_auto_transcript_badge_does_not_claim_language_id(qt_app: QApplication) -> None:
    del qt_app
    panel = TranscriptPanel()
    panel.set_transcript(
        "नमस्ते",
        {
            "language_code": "auto",
            "script_label": "Devanagari",
            "language_note": "Script hint only — Devanagari is shared by multiple languages.",
            "words": 1,
        },
    )
    assert panel.language_badge.text() == "DEVANAGARI SCRIPT"
    assert "Hindi" not in panel.language_badge.text()
    assert "Script hint only" in panel.script_note.text()


def test_transcript_actions_copy_send_and_clear(qt_app: QApplication) -> None:
    page = DictatePage()
    sent: list[str] = []
    cleared: list[bool] = []
    page.notes_requested.connect(sent.append)
    page.clear_requested.connect(lambda: cleared.append(True))
    page.show_transcript("A useful local transcript.", {"words": 4, "language_code": "auto"})

    page.transcript_panel.copy_button.click()
    assert qt_app.clipboard().text() == "A useful local transcript."
    page.transcript_panel.notes_button.click()
    assert sent == ["A useful local transcript."]
    page.transcript_panel.clear_button.click()
    assert cleared == [True]
    assert page.transcript_panel.text == ""


def test_recording_panel_exposes_model_states(qt_app: QApplication) -> None:
    del qt_app
    page = DictatePage()
    page.set_engine_status("loading", "Loading speech model on CPU")
    assert page.recording.state_label.text() == "LOADING"
    assert not page.recording.record_button.isEnabled()

    page.set_engine_status("ready", "CPU / fp32")
    assert page.recording.state_label.text() == "READY"
    assert page.recording.record_button.isEnabled()

    page.set_engine_status("failed", "Model cache unavailable")
    assert page.recording.state_label.text() == "ERROR"
    assert page.recording.record_button.text() == "Unavailable"


def test_voice_meter_only_animates_for_current_recording(qt_app: QApplication) -> None:
    del qt_app
    page = DictatePage()
    page.set_engine_status("ready", "CPU / fp32")
    snapshot = SimpleNamespace(
        level=0.08,
        peak=0.99,
        elapsed=1.2,
        waveform=(0.0, 0.2, 0.8, 1.0),
    )

    page.set_recording_state("listening", "Notepad")
    page.set_audio_snapshot(snapshot)
    assert page.recording.input_state.text() == "CLIPPING"
    assert max(page.recording.level._levels) > 0.0
    assert page.recording.elapsed_label.text() == "00:01"
    assert "CURRENT RECORDING" in page.recording.mic_state.text()

    page.set_recording_state("processing", "Processing locally")
    assert page.recording.input_state.text() == "QUIET"
    assert max(page.recording.level._levels) == 0.0
    assert page.recording.elapsed_label.text() == "00:00"
    assert "AMBIENT ONLY" in page.recording.mic_state.text()


def test_processing_marks_existing_text_as_previous_transcript(qt_app: QApplication) -> None:
    del qt_app
    page = DictatePage()
    page.show_transcript(
        "మునుపటి వాక్యం",
        {"words": 2, "language_code": "auto", "script_label": "Telugu"},
    )

    page.set_recording_state("processing", "Processing new audio")
    assert page.transcript_panel.text == "మునుపటి వాక్యం"
    assert page.transcript_panel.eyebrow.text() == "PREVIOUS TRANSCRIPT"
    assert page.transcript_panel.language_badge.text() == "TELUGU SCRIPT"

    page.show_transcript(
        "New result", {"words": 2, "language_code": "en", "language_name": "English"}
    )
    assert page.transcript_panel.eyebrow.text() == "LATEST TRANSCRIPT"
    assert page.transcript_panel.text == "New result"


def test_shortcut_keycaps_render_configured_values(qt_app: QApplication) -> None:
    del qt_app
    page = DictatePage()
    page.apply_snapshot(
        {
            "hotkey_ptt": "Right Ctrl",
            "hotkey_toggle": "F8",
            "hotkey_paste_last": "F10",
            "hotkey_cancel": "Pause",
        }
    )
    assert {key: label.text() for key, label in page.recording.shortcut_keycaps.items()} == {
        "ptt": "Right Ctrl",
        "toggle": "F8",
        "paste": "F10",
        "cancel": "Pause",
    }
