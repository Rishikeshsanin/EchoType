from __future__ import annotations

import sys

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication

from echotype import __version__
from echotype.app.runtime import DictationRuntime
from echotype.services.diagnostics import DiagnosticsService
from echotype.ui.main_window import MainWindow
from echotype.ui.overlay import RecordingOverlay
from echotype.ui.pages.history import HistoryPage
from echotype.ui.pages.notes import NotesPage
from echotype.ui.pages.settings import SettingsPage
from echotype.ui.pages.vocabulary import VocabularyPage
from echotype.ui.theme import stylesheet


def main() -> int:
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("EchoType")
    app.setApplicationVersion(__version__)
    app.setOrganizationName("EchoType")
    app.setStyle("Fusion")

    runtime = DictationRuntime()
    app.setStyleSheet(stylesheet(runtime.settings.get("theme", "system")))
    diagnostics = DiagnosticsService(
        runtime.settings,
        audio=runtime.audio,
        engine=runtime.engine,
        runtime=runtime,
    )
    settings_page = SettingsPage(
        runtime.settings,
        diagnostics,
        audio=runtime.audio,
        engine=runtime.engine,
        history=runtime.history,
        on_audio_changed=runtime.refresh_audio,
        on_hotkeys_changed=runtime.refresh_hotkeys,
    )
    vocabulary_page = VocabularyPage(runtime.vocabulary)
    history_page = HistoryPage(runtime.history)
    notes_page = NotesPage(history_store=runtime.history)
    window = MainWindow(
        history_page=history_page,
        notes_page=notes_page,
        settings_page=settings_page,
        vocabulary_page=vocabulary_page,
        default_mode=str(runtime.settings.get("default_mode", "smart")),
    )
    overlay = RecordingOverlay(runtime.audio)

    window.mode_changed.connect(runtime.set_mode)
    window.language_changed.connect(runtime.set_language)
    window.record_pressed.connect(runtime.begin_recording)
    window.record_released.connect(runtime.end_recording)
    window.paste_requested.connect(runtime.paste_last)
    window.clear_requested.connect(runtime.clear_last)
    history_page.repaste_requested.connect(runtime.repaste_text)
    history_page.status_message.connect(window.show_status)
    notes_page.status_message.connect(window.show_status)
    runtime.engine_status.connect(window.set_engine_status)
    runtime.recording_state.connect(window.set_recording_state)
    runtime.overlay_state.connect(overlay.set_state)
    runtime.transcript_ready.connect(window.show_transcript)
    runtime.transcript_ready.connect(lambda _text, _metadata: history_page.refresh())
    runtime.service_warning.connect(window.show_warning)
    runtime.audio_level.connect(window.set_audio_level)
    runtime.audio_snapshot.connect(window.set_audio_snapshot)
    app.aboutToQuit.connect(runtime.shutdown)

    window.apply_runtime_snapshot(runtime.ui_snapshot())

    window.show()
    # Capture EchoType's HWND on the UI thread; the injection service can then
    # avoid ever pasting a transcript back into EchoType itself.
    runtime.set_own_hwnds({int(window.winId()), int(overlay.winId())})

    # Let the first frame paint before model loading/microphone setup begins.
    QTimer.singleShot(0, runtime.start)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
