from __future__ import annotations

import os

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
