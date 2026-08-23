from __future__ import annotations

import sys

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication

from echotype.app.runtime import DictationRuntime
from echotype.ui.main_window import MainWindow
from echotype.ui.overlay import RecordingOverlay
from echotype.ui.theme import stylesheet


def main() -> int:
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("EchoType")
    app.setOrganizationName("EchoType")
    app.setStyle("Fusion")
    app.setStyleSheet(stylesheet())

    runtime = DictationRuntime()
    window = MainWindow()
    overlay = RecordingOverlay(runtime.audio)

    window.mode_changed.connect(runtime.set_mode)
    window.record_pressed.connect(runtime.begin_recording)
    window.record_released.connect(runtime.end_recording)
    runtime.engine_status.connect(window.set_engine_status)
    runtime.recording_state.connect(window.set_recording_state)
    runtime.overlay_state.connect(overlay.set_state)
    runtime.transcript_ready.connect(window.show_transcript)
    runtime.service_warning.connect(window.show_warning)
    app.aboutToQuit.connect(runtime.shutdown)

    window.show()
    # Capture EchoType's HWND on the UI thread; the injection service can then
    # avoid ever pasting a transcript back into EchoType itself.
    runtime.set_own_hwnds({int(window.winId()), int(overlay.winId())})

    # Let the first frame paint before model loading/microphone setup begins.
    QTimer.singleShot(0, runtime.start)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
