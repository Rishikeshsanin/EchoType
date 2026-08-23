from __future__ import annotations

import threading
import time

from PySide6.QtCore import QObject, QTimer, Signal, Slot

from echotype.core.audio import SAMPLE_RATE, AudioEngine, AudioError
from echotype.core.cleanup import MODES, SMART, word_count
from echotype.core.languages import AUTO, BY_CODE, describe, name_for_code
from echotype.core.transcription import BUSY, READY, Result, TranscriptionEngine
from echotype.services.history import HistoryStore
from echotype.services.hotkeys import HotkeyManager, label_for
from echotype.services.injection import Injector, capture_focus
from echotype.services.settings import Settings
from echotype.services.vocabulary import VocabularyService


def external_capture_target(
    captured: object, own_hwnds: set[int], fallback: object | None = None
) -> object | None:
    """Never treat an EchoType-owned window as the external dictation target."""
    hwnd = getattr(captured, "hwnd", None)
    return fallback if hwnd and int(hwnd) in own_hwnds else captured


class DictationRuntime(QObject):
    """Coordinates EchoType's engine without coupling services to UI widgets."""

    engine_status = Signal(str, str)
    recording_state = Signal(str, str)
    overlay_state = Signal(str, object)
    transcript_ready = Signal(str, object)
    service_warning = Signal(str, str)
    audio_level = Signal(float, float)
    audio_snapshot = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self.settings = Settings()
        self.history = HistoryStore(settings=self.settings)
        self.vocabulary = VocabularyService(legacy_terms=self.settings.get("vocabulary"))
        self.audio = AudioEngine(self.settings)
        self.engine = TranscriptionEngine(
            self.settings,
            on_status=self._on_engine_status,
            on_result=self._on_engine_result,
            vocabulary=self.vocabulary,
        )
        self.injector = Injector(self.settings, own_hwnds=lambda: set(self._own_hwnds))
        self.hotkeys = HotkeyManager(
            self.settings,
            on_ptt_down=self._ptt_down,
            on_ptt_up=self._ptt_up,
            on_toggle=self.toggle_recording,
            on_paste_last=self.paste_last,
            on_cancel=self.cancel_recording,
        )

        self.mode = str(self.settings.get("default_mode", SMART))
        self._recording = False
        self._recording_lock = threading.Lock()
        self._ending = False
        self._toggle_mode = False
        self._recording_language = AUTO
        self._target = None
        self._last_external_target = None
        self._last_text = ""
        self._last_target = None
        self._own_hwnds: set[int] = set()
        self._started = False
        self._level_timer = QTimer(self)
        self._level_timer.setInterval(60)
        self._level_timer.timeout.connect(self._emit_audio_level)
        self._dictation_sequence = 0
        self._active_overlay_tag = ""
        self._timing_lock = threading.Lock()
        self._capture_timing: dict[str, float] = {}

    @staticmethod
    def _overlay_payload(target=None, **values) -> dict[str, object]:
        return {
            "target_hwnd": getattr(target, "hwnd", None),
            "target_title": getattr(target, "title", "") or "",
            "target_process": getattr(target, "process_name", "") or "",
            **values,
        }

    def _emit_overlay_for(self, tag: str, state: str, payload: dict[str, object]) -> None:
        if tag == self._active_overlay_tag:
            self.overlay_state.emit(state, payload)

    def _mark_capture(self, event: str, when: float | None = None) -> None:
        with self._timing_lock:
            self._capture_timing[event] = float(when or time.perf_counter())

    @property
    def capture_timing(self) -> dict[str, float]:
        """Latest monotonic PTT/capture timeline for diagnostics and tests."""
        with self._timing_lock:
            return dict(self._capture_timing)

    @property
    def capture_stop_latency_ms(self) -> float | None:
        timing = self.capture_timing
        released = timing.get("ptt_key_up")
        closed = timing.get("recording_buffer_closed")
        if released is None or closed is None or closed < released:
            return None
        return max(0.0, (closed - released) * 1_000.0)

    @property
    def capture_timing_ms(self) -> dict[str, float]:
        timing = self.capture_timing
        origin = timing.get("ptt_key_down")
        if origin is None:
            return {}
        return {name: max(0.0, (value - origin) * 1_000.0) for name, value in timing.items()}

    def _ptt_down(self) -> None:
        with self._timing_lock:
            self._capture_timing = {
                "ptt_key_down": float(self.hotkeys.last_ptt_down_at or time.perf_counter())
            }
        self.begin_recording()

    def _ptt_up(self) -> None:
        self._mark_capture("ptt_key_up", self.hotkeys.last_ptt_up_at)
        self.end_recording()

    def set_own_hwnds(self, hwnds: set[int]) -> None:
        self._own_hwnds = {int(hwnd) for hwnd in hwnds if hwnd}

    @Slot()
    def start(self) -> None:
        if self._started:
            return
        self._started = True
        self._level_timer.start()
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

    @Slot(str)
    def set_language(self, code: str) -> None:
        normalized = str(code or AUTO).strip().lower()
        if normalized not in BY_CODE:
            normalized = AUTO
        try:
            self.settings.set("language", normalized)
            self.engine.reset_language_memory()
        except (OSError, TypeError, ValueError) as exc:
            self.service_warning.emit("Language preference could not be saved", str(exc))

    def ui_snapshot(self) -> dict[str, object]:
        """Return presentation-safe startup state without exposing services."""
        return {
            "language": self.settings.get("language", AUTO),
            "mode": self.mode,
            "hotkey_ptt": label_for(self.settings.get("hotkey_ptt")),
            "hotkey_toggle": label_for(self.settings.get("hotkey_toggle")),
            "hotkey_paste_last": label_for(self.settings.get("hotkey_paste_last")),
            "hotkey_cancel": label_for(self.settings.get("hotkey_cancel")),
            "history": self.history.recent(3),
        }

    @Slot()
    def clear_last(self) -> None:
        self._last_text = ""
        self._last_target = None

    @Slot()
    def _emit_audio_level(self) -> None:
        snapshot = self.audio.snapshot()
        self.audio_level.emit(float(snapshot.level), float(snapshot.elapsed))
        self.audio_snapshot.emit(snapshot)

    @Slot()
    def refresh_audio(self) -> None:
        """Apply a changed input device without restarting the whole runtime."""
        if not self._started or self._recording:
            return
        try:
            self.audio.start()
        except AudioError as exc:
            self.service_warning.emit("Microphone unavailable", str(exc))

    @Slot()
    def refresh_hotkeys(self) -> None:
        self.hotkeys.refresh()

    def _engine_ready(self) -> bool:
        return self.engine.status == READY and self.engine.model is not None

    @Slot()
    def begin_recording(self) -> None:
        with self._recording_lock:
            if self._recording or self._ending:
                return
        if self.engine.status == BUSY:
            self.recording_state.emit("processing", "Finish the current transcription first")
            self.overlay_state.emit(
                "error",
                {"detail": "Speech model is busy", "dismiss_ms": 900},
            )
            return
        if not self._engine_ready():
            self.recording_state.emit("loading", "Speech model is still loading")
            self.overlay_state.emit(
                "error",
                {"detail": "Speech model is still loading", "dismiss_ms": 1_100},
            )
            return
        if not self.audio.running:
            try:
                self.audio.start()
            except AudioError as exc:
                self.service_warning.emit("Microphone unavailable", str(exc))
                self.recording_state.emit("ready", "Microphone unavailable")
                self.overlay_state.emit(
                    "error",
                    {"detail": "Microphone unavailable", "dismiss_ms": 1_200},
                )
                return

        raw_capture = capture_focus()
        captured = external_capture_target(raw_capture, self._own_hwnds, self._last_external_target)
        captured_hwnd = getattr(captured, "hwnd", None)
        if captured is raw_capture and captured_hwnd:
            self._last_external_target = captured
        self._target = captured
        self._dictation_sequence += 1
        self._active_overlay_tag = str(self._dictation_sequence)
        self._recording_language = str(self.settings.get("language", AUTO) or AUTO)
        with self._recording_lock:
            if self._recording or self._ending:
                return
            self._recording = True
        self.audio.begin()
        self._mark_capture("audio_begin", self.audio.last_begin_at)
        target_name = getattr(self._target, "title", "") or "active app"
        self.recording_state.emit("listening", target_name[:80])
        self.overlay_state.emit("listening", self._overlay_payload(self._target))

    @Slot()
    def end_recording(self) -> None:
        with self._recording_lock:
            if not self._recording or self._ending:
                return
            self._ending = True
        self._mark_capture("end_recording_entry")

        audio = self.audio.end()
        self._mark_capture("audio_end_entry", self.audio.last_end_entry_at)
        self._mark_capture("recording_buffer_closed", self.audio.last_buffer_closed_at)
        with self._recording_lock:
            self._recording = False
            self._ending = False
        self._mark_capture("runtime_recording_false")
        self._toggle_mode = False
        seconds = audio.size / float(SAMPLE_RATE)
        minimum = float(self.settings.get("min_record_seconds", 0.35))
        held_seconds = float(self.audio.last_capture_seconds)
        if held_seconds < minimum:
            self.recording_state.emit("ready", f"Clip too short ({held_seconds:.2f}s)")
            self.overlay_state.emit(
                "cancelled",
                self._overlay_payload(
                    self._target,
                    detail=f"Clip too short ({held_seconds:.2f}s)",
                    dismiss_ms=850,
                ),
            )
            return

        target = self._target
        mode = self.mode
        language = self._recording_language
        tag = self._active_overlay_tag
        self.recording_state.emit("processing", f"Processing {seconds:.1f}s of speech")
        self._mark_capture("processing_state")
        self.overlay_state.emit("processing", self._overlay_payload(target))
        threading.Thread(
            target=self._process_and_submit,
            args=(audio, target, mode, language, tag),
            name="echotype-audio-process",
            daemon=True,
        ).start()

    def _process_and_submit(self, audio, target, mode: str, language: str, tag: str) -> None:
        try:
            processed, info = self.audio.process(audio)
            self.engine.submit(
                processed,
                info,
                target=target,
                mode=mode,
                language=language,
                tag=tag,
            )
        except Exception as exc:  # noqa: BLE001 - service boundary must keep the UI alive
            self.service_warning.emit("Audio processing failed", str(exc))
            self.recording_state.emit("ready", "Audio processing failed")
            self._emit_overlay_for(
                tag,
                "error",
                self._overlay_payload(target, detail="Audio processing failed"),
            )

    @Slot()
    def toggle_recording(self) -> None:
        if self._recording:
            self.end_recording()
            return
        self._toggle_mode = True
        self.begin_recording()

    @Slot()
    def cancel_recording(self) -> None:
        with self._recording_lock:
            if not self._recording or self._ending:
                return
            self._ending = True
        self.audio.cancel()
        with self._recording_lock:
            self._recording = False
            self._ending = False
        self._toggle_mode = False
        self.recording_state.emit("ready", "Recording cancelled")
        self.overlay_state.emit(
            "cancelled",
            self._overlay_payload(self._target, detail="Recording cancelled", dismiss_ms=700),
        )

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
            state = "cancelled" if result.error in {"too_short", "no_speech"} else "error"
            self._emit_overlay_for(
                result.job.tag,
                state,
                self._overlay_payload(result.job.target, detail=friendly),
            )
            return

        self._last_text = result.text
        self._last_target = result.job.target
        info = result.job.info or {}
        # A selection change made while this job was processing applies to the
        # next utterance. Metadata and decoder constraints stay paired with the
        # language captured when this recording began.
        language_code = str(
            getattr(result.job, "language", None) or self.settings.get("language", AUTO) or AUTO
        )
        language_info = describe(result.text, language_code)
        script = language_info.get("script")
        if language_code == AUTO:
            language_name = ""
            language_note = str(language_info.get("note") or "")
        else:
            language_name = name_for_code(language_code)
            language_note = str(language_info.get("note") or "")
            if not language_note:
                language_note = (
                    f"{language_name} was selected manually; "
                    "language was not independently identified."
                )
        words = word_count(result.text)
        audio_seconds = float(info.get("seconds", 0.0))
        typing_seconds_saved = max(0.0, words / 40.0 * 60.0 - audio_seconds)
        metadata = {
            "mode": result.job.mode,
            "raw": result.raw,
            "elapsed": result.elapsed,
            "rtf": result.elapsed / max(audio_seconds, 1e-6),
            "audio_seconds": audio_seconds,
            "snr_db": info.get("snr_db"),
            "denoised": bool(info.get("denoised", False)),
            "cleanup_changed": result.changed_by_cleanup,
            "target": getattr(result.job.target, "title", "") or "",
            "device": self.engine.device,
            "precision": self.engine.precision,
            "time": time.time(),
            "words": words,
            "typing_seconds_saved": typing_seconds_saved,
            "language_code": language_code,
            "language_name": language_name,
            "script": script,
            "script_label": language_info.get("script_label"),
            "language_note": language_note,
            "language_mismatch": bool(language_info.get("mismatch", False)),
        }

        if self.settings.get("history_enabled", True) and not self.settings.get(
            "private_session", False
        ):
            try:
                self.history.append({"text": result.text, **metadata})
                self.history.prune(int(self.settings.get("history_retention_days", 0)))
            except Exception as exc:
                self.service_warning.emit("History could not be saved", str(exc))

        self.transcript_ready.emit(result.text, metadata)
        self.recording_state.emit("ready", "Transcript ready")

        if self.settings.get("auto_copy", True) or self.settings.get("auto_paste", True):
            threading.Thread(
                target=self._deliver_and_finish,
                args=(result.text, result.job.target, result.job.tag),
                name="echotype-delivery",
                daemon=True,
            ).start()
        else:
            self._emit_overlay_for(
                result.job.tag,
                "success",
                self._overlay_payload(result.job.target, detail="Transcript ready"),
            )

    def _deliver_and_finish(self, text: str, target, tag: str) -> None:
        try:
            delivery = self.injector.deliver(text, target)
        except Exception as exc:  # noqa: BLE001 - delivery integrates OS APIs
            self.service_warning.emit("Transcript delivery failed", str(exc))
            self._emit_overlay_for(
                tag,
                "error",
                self._overlay_payload(target, detail="Transcript delivery failed"),
            )
            return

        if delivery.get("pasted"):
            detail = "Pasted"
            state = "success"
        elif self.settings.get("auto_paste", True):
            reasons = {
                "no_target": "Target application unavailable",
                "own_window": "Transcript ready in EchoType",
                "focus_failed": "Could not restore target application",
                "clipboard_failed": "Could not copy transcript",
                "clipboard_changed": "Clipboard changed before paste",
                "sensitive_target": "Sensitive field detected; not pasted",
            }
            detail = reasons.get(str(delivery.get("reason", "")), "Could not paste transcript")
            state = "success" if delivery.get("reason") == "own_window" else "error"
            if delivery.get("copied") and state == "error":
                detail = f"{detail}; copied instead"
        elif delivery.get("copied"):
            detail = "Copied"
            state = "success"
        elif self.settings.get("auto_copy", True):
            detail = "Could not copy transcript"
            state = "error"
        else:
            detail = "Transcript ready"
            state = "success"
        self._emit_overlay_for(tag, state, self._overlay_payload(target, detail=detail))

    @Slot()
    def shutdown(self) -> None:
        if not self._started:
            return
        self._started = False
        self._level_timer.stop()
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
