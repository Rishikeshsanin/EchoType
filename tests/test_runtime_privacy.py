from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]


class FakeSignal:
    def __init__(self, *_args) -> None:
        self.calls: list[tuple[object, ...]] = []

    def emit(self, *args) -> None:
        self.calls.append(args)

    def connect(self, _callback) -> None:
        pass


class FakeTimer:
    def __init__(self, *_args) -> None:
        self.timeout = FakeSignal()

    def setInterval(self, _interval: int) -> None:
        pass

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass


class FakeSettings:
    def __init__(self, **values) -> None:
        self.values = values

    def get(self, key: str, default=None):
        return self.values.get(key, default)


class FakeHistory:
    def __init__(self) -> None:
        self.entries: list[dict] = []

    def append(self, entry: dict) -> None:
        self.entries.append(entry)

    def prune(self, _days: int) -> int:
        return 0


def load_runtime(monkeypatch):
    qt_core = ModuleType("PySide6.QtCore")
    qt_core.QObject = object
    qt_core.QTimer = FakeTimer
    qt_core.Signal = FakeSignal
    qt_core.Slot = lambda *_args: lambda function: function
    pyside = ModuleType("PySide6")
    pyside.QtCore = qt_core
    monkeypatch.setitem(sys.modules, "PySide6", pyside)
    monkeypatch.setitem(sys.modules, "PySide6.QtCore", qt_core)

    audio = ModuleType("echotype.core.audio")
    audio.AudioEngine = object
    audio.AudioError = RuntimeError
    audio.SAMPLE_RATE = 16_000
    monkeypatch.setitem(sys.modules, "echotype.core.audio", audio)

    transcription = ModuleType("echotype.core.transcription")
    transcription.BUSY = "busy"
    transcription.READY = "ready"
    transcription.Result = object
    transcription.TranscriptionEngine = object
    monkeypatch.setitem(sys.modules, "echotype.core.transcription", transcription)

    hotkeys = ModuleType("echotype.services.hotkeys")
    hotkeys.HotkeyManager = object
    hotkeys.label_for = lambda value: str(value or "")
    monkeypatch.setitem(sys.modules, "echotype.services.hotkeys", hotkeys)

    injection = ModuleType("echotype.services.injection")
    injection.Injector = object
    injection.capture_focus = lambda: None
    monkeypatch.setitem(sys.modules, "echotype.services.injection", injection)

    module_name = "_echotype_runtime_under_test"
    spec = importlib.util.spec_from_file_location(
        module_name, ROOT / "src" / "echotype" / "app" / "runtime.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, module_name, module)
    spec.loader.exec_module(module)
    return module


def make_runtime(module, *, history_enabled: bool, private_session: bool):
    runtime = object.__new__(module.DictationRuntime)
    runtime.settings = FakeSettings(
        history_enabled=history_enabled,
        private_session=private_session,
        auto_copy=False,
        auto_paste=False,
        language="auto",
        history_retention_days=0,
    )
    runtime.history = FakeHistory()
    runtime.engine = SimpleNamespace(device="cpu", precision="fp32")
    runtime.injector = SimpleNamespace(deliver=lambda *_args: None)
    runtime.transcript_ready = FakeSignal()
    runtime.recording_state = FakeSignal()
    runtime.service_warning = FakeSignal()
    runtime.overlay_state = FakeSignal()
    runtime._last_text = ""
    runtime._last_target = None
    runtime._active_overlay_tag = ""
    return runtime


def make_result(*, audio_seconds: float = 4.0):
    target = SimpleNamespace(title="Notepad")
    job = SimpleNamespace(
        mode="verbatim",
        target=target,
        tag="",
        info={"seconds": audio_seconds, "snr_db": 17.0, "denoised": True},
    )
    return SimpleNamespace(
        ok=True,
        text="literal transcript",
        raw="literal transcript",
        elapsed=1.0,
        changed_by_cleanup=False,
        job=job,
    )


def test_private_session_does_not_write_history_but_still_emits_transcript(monkeypatch) -> None:
    module = load_runtime(monkeypatch)
    runtime = make_runtime(module, history_enabled=True, private_session=True)
    runtime._on_engine_result(make_result())

    assert runtime.history.entries == []
    assert runtime.transcript_ready.calls[0][0] == "literal transcript"


def test_history_disabled_does_not_write_history(monkeypatch) -> None:
    module = load_runtime(monkeypatch)
    runtime = make_runtime(module, history_enabled=False, private_session=False)
    runtime._on_engine_result(make_result())
    assert runtime.history.entries == []


def test_runtime_persists_and_emits_calculated_transcript_metadata(monkeypatch) -> None:
    module = load_runtime(monkeypatch)
    runtime = make_runtime(module, history_enabled=True, private_session=False)
    runtime._on_engine_result(make_result(audio_seconds=4.0))

    assert len(runtime.history.entries) == 1
    saved = runtime.history.entries[0]
    assert saved["text"] == "literal transcript"
    assert saved["raw"] == "literal transcript"
    assert saved["elapsed"] == 1.0
    assert saved["audio_seconds"] == 4.0
    assert saved["rtf"] == 0.25
    assert saved["snr_db"] == 17.0
    assert saved["denoised"] is True
    assert saved["target"] == "Notepad"
    assert saved["device"] == "cpu"
    assert saved["precision"] == "fp32"
    assert runtime.transcript_ready.calls[0][1] == {
        key: saved[key] for key in saved if key != "text"
    }
