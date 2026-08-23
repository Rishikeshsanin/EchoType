from __future__ import annotations

import threading

from PySide6.QtCore import QObject, Signal, Slot

from echotype.core.audio import SAMPLE_RATE, AudioEngine, AudioError
from echotype.core.cleanup import MODES, SMART
from echotype.core.transcription import BUSY, READY, Result, TranscriptionEngine
from echotype.services.history import HistoryStore
from echotype.services.hotkeys import HotkeyManager
from echotype.services.injection import Injector, capture_focus
from echotype.services.settings import Settings


class DictationRuntime(QObject):
    """Coordinates EchoType's engine without coupling services to UI widgets."""

    engine_status = Signal(str, str)
    recording_state = Signal(str, str)
    transcript_ready = Signal(str, object)
    service_warning = Signal(str, str)

    def __init__(self) -> None:
        super().__init__()
        self.settings = Settings()
        self.history = HistoryStore(settings=self.settings)
        self.audio = AudioEngine(self.settings)
        self.engine = TranscriptionEngine(
            self.settings,
            on_status=self._on_engine_status,
            on_result=self._on_engine_result,
        )
        self.injector = Injector(self.settings, own_hwnds=lambda: set(self._own_hwnds))
        self.hotkeys = HotkeyManager(
            self.settings,
            on_ptt_down=self.begin_recording,
            on_ptt_up=self.end_recording,
            on_toggle=self.toggle_recording,
            on_paste_last=self.paste_last,
            on_cancel=self.cancel_recording,
        )

        self.mode = SMART
        self._recording = False
        self._toggle_mode = False
        self._target = None
        self._last_text = ""
        self._last_target = None
        self._own_hwnds: set[int] = set()
        self._started = False

    def set_own_hwnds(self, hwnds: set[int]) -> None:
        self._own_hwnds = {int(hwnd) for hwnd in hwnds if hwnd}

    @Slot()
    def start(self) -> None:
        if self._started:
            return
        self._started = True
        self.engine.start()

        try:
            self.audio.start()
        except AudioError as exc:
            self.service_warning.emit("Microphone unavailable", str(exc))

        if not self.hotkeys.start():
            self.service_warning.emit(
                "Global shortcuts unavailable",
                self.hotkeys.last_error or "Unknown keyboard hook error",
            )

    @Slot(str)
    def set_mode(self, mode: str) -> None:
        normalized = str(mode).strip().lower()
        self.mode = normalized if normalized in MODES else SMART

    def _engine_ready(self) -> bool:
        return self.engine.status in (READY, BUSY) and self.engine.model is not None

    @Slot()
    def begin_recording(self) -> None:
        if self._recording:
            return
        if not self._engine_ready():
            self.recording_state.emit("loading", "Speech model is still loading")
            return
        if not self.audio.running:
            try:
                self.audio.start()
            except AudioError as exc:
                self.service_warning.emit("Microphone unavailable", str(exc))
                return

        self._target = capture_focus()
        self._recording = True
        self.audio.begin()
        target_name = getattr(self._target, "title", "") or "active app"
        self.recording_state.emit("listening", target_name[:80])

    @Slot()
    def end_recording(self) -> None:
        if not self._recording:
            return
        self._recording = False
        self._toggle_mode = False

        audio = self.audio.end()
        seconds = audio.size / float(SAMPLE_RATE)
        minimum = float(self.settings.get("min_record_seconds", 0.35))
        if seconds < minimum:
            self.recording_state.emit("ready", f"Clip too short ({seconds:.2f}s)")
            return

        target = self._target
        mode = self.mode
        self.recording_state.emit("processing", f"Processing {seconds:.1f}s of speech")
        threading.Thread(
            target=self._process_and_submit,
            args=(audio, target, mode),
            name="echotype-audio-process",
            daemon=True,
        ).start()

    def _process_and_submit(self, audio, target, mode: str) -> None:
        try:
            processed, info = self.audio.process(audio)
            self.engine.submit(processed, info, target=target, mode=mode)
        except Exception as exc:
            self.service_warning.emit("Audio processing failed", str(exc))
            self.recording_state.emit("ready", "Audio processing failed")

    @Slot()
    def toggle_recording(self) -> None:
        if self._recording:
            self.end_recording()
            return
        self._toggle_mode = True
        self.begin_recording()

    @Slot()
    def cancel_recording(self) -> None:
        if not self._recording:
            return
        self.audio.cancel()
        self._recording = False
        self._toggle_mode = False
        self.recording_state.emit("ready", "Recording cancelled")

    @Slot()
    def paste_last(self) -> None:
        if not self._last_text:
            return
        self.repaste_text(self._last_text)

    @Slot(str, object)
    def repaste_text(self, text: str, _entry: object = None) -> None:
        """Paste page-selected history text into the last captured external app."""
        if not text:
            return
        target = self._last_target or self._target
        threading.Thread(
            target=self.injector.deliver,
            args=(text, target),
            name="echotype-repaste",
            daemon=True,
        ).start()

    def _on_engine_status(self, status: str, detail: str) -> None:
        self.engine_status.emit(status, detail)
        if status == READY and not self._recording:
            self.recording_state.emit("ready", "Hold Right Shift to speak")

    def _on_engine_result(self, result: Result) -> None:
        if not result.ok:
            friendly = {
                "too_short": "Speech was too short",
                "no_speech": "No speech detected",
            }.get(result.error or "", result.error or "Transcription failed")
            self.recording_state.emit("ready", friendly)
            return

        self._last_text = result.text
        self._last_target = result.job.target
        info = result.job.info or {}
        metadata = {
            "mode": result.job.mode,
            "raw": result.raw,
            "elapsed": result.elapsed,
            "rtf": result.elapsed / max(float(info.get("seconds", 0.0)), 1e-6),
            "audio_seconds": float(info.get("seconds", 0.0)),
            "snr_db": info.get("snr_db"),
            "denoised": bool(info.get("denoised", False)),
            "cleanup_changed": result.changed_by_cleanup,
            "target": getattr(result.job.target, "title", "") or "",
            "device": self.engine.device,
            "precision": self.engine.precision,
        }

        try:
            self.history.append({"text": result.text, **metadata})
        except Exception as exc:
            self.service_warning.emit("History could not be saved", str(exc))

        self.transcript_ready.emit(result.text, metadata)
        self.recording_state.emit("ready", "Transcript ready")

        if self.settings.get("auto_copy", True) or self.settings.get("auto_paste", True):
            threading.Thread(
                target=self.injector.deliver,
                args=(result.text, result.job.target),
                name="echotype-delivery",
                daemon=True,
            ).start()

    @Slot()
    def shutdown(self) -> None:
        if not self._started:
            return
        self._started = False
        try:
            self.hotkeys.stop()
        except Exception:
            pass
        try:
            self.audio.stop()
        except Exception:
            pass
        try:
            self.engine.shutdown()
        except Exception:
            pass
