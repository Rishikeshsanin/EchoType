from __future__ import annotations

import os
from types import SimpleNamespace

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from echotype.core.audio import AudioEngine
from echotype.ui.overlay import (
    CANCELLED,
    ERROR,
    HIDDEN,
    LISTENING,
    PROCESSING,
    SUCCESS,
    RecordingOverlay,
    format_elapsed,
    target_display_name,
)


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    app = QApplication.instance() or QApplication([])
    return app


class FakeAudio:
    def snapshot(self) -> SimpleNamespace:
        return SimpleNamespace(
            elapsed=2.46,
            level=0.12,
            peak=0.4,
            waveform=(0.0, 0.2, 0.6, 0.3),
        )


class FakeSettings:
    def get(self, key: str, default: object = None) -> object:
        del key
        return default


def test_audio_snapshot_is_hardware_independent() -> None:
    snapshot = AudioEngine(FakeSettings()).snapshot()
    assert snapshot.level == 0.0
    assert snapshot.peak == 0.0
    assert snapshot.elapsed == 0.0
    assert len(snapshot.waveform) == 72


def test_elapsed_formatter() -> None:
    assert format_elapsed(0) == "00.0"
    assert format_elapsed(2.46) == "02.5"
    assert format_elapsed(2.46, suffix=True) == "2.5s"
    assert format_elapsed(62.46) == "1:02.5"
    assert format_elapsed(-5) == "00.0"


@pytest.mark.parametrize(
    ("title", "process_name", "expected"),
    [
        ("Untitled - Notepad", "notepad.exe", "Notepad"),
        ("EchoType - Google Chrome", "chrome.exe", "Google Chrome"),
        ("overlay.py - EchoType - Visual Studio Code", "Code.exe", "Visual Studio Code"),
        ("Budget - LibreOffice Writer", "soffice.bin", "Soffice"),
        ("Document - Paint", "", "Paint"),
        ("", "", "Active application"),
    ],
)
def test_target_display_name(title: str, process_name: str, expected: str) -> None:
    assert target_display_name(title, process_name) == expected


def test_overlay_state_transitions(qapp: QApplication) -> None:
    overlay = RecordingOverlay(FakeAudio())

    overlay.set_state(LISTENING, {"target_title": "Draft - Notepad"})
    qapp.processEvents()
    assert overlay.current_state == LISTENING
    assert overlay.state_label.text() == "LISTENING"
    assert overlay.target_label.text() == "Notepad"
    assert overlay.timer_label.text() == "02.5"
    assert overlay.meter.isVisible()

    overlay.set_state(PROCESSING, {"target_process": "chrome.exe"})
    qapp.processEvents()
    assert overlay.current_state == PROCESSING
    assert overlay.state_label.text() == "TRANSCRIBING"
    assert overlay.detail_label.text() == "Processing locally"
    assert overlay.target_label.text() == "Google Chrome"
    assert overlay.timer_label.text().endswith("s")

    overlay.set_state(SUCCESS, {"detail": "Pasted", "dismiss_ms": 5_000})
    qapp.processEvents()
    assert overlay.current_state == SUCCESS
    assert overlay.detail_label.text() == "Pasted"

    overlay.set_state(CANCELLED, {"detail": "Recording cancelled", "dismiss_ms": 5_000})
    qapp.processEvents()
    assert overlay.current_state == CANCELLED

    overlay.set_state(ERROR, {"detail": "Could not paste transcript", "dismiss_ms": 5_000})
    qapp.processEvents()
    assert overlay.current_state == ERROR
    assert overlay.detail_label.text() == "Could not paste transcript"

    overlay.set_state(HIDDEN)
    qapp.processEvents()
    assert overlay.current_state == HIDDEN
    assert not overlay.isVisible()
    overlay.close()
